"""Model backend abstraction for STUTT.

The language layer remains separate from reasoning model execution.
This module intentionally provides a narrow interface so new providers can be
added without changing STUTT control flow.
"""

from __future__ import annotations

import ipaddress
import json
import math
import os
import re
import ssl
import stat
from abc import ABC, abstractmethod
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from typing import Any, Mapping
from urllib import error, request
from urllib.parse import urlsplit


DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_OPENAI_CHAT_PATH = "/v1/chat/completions"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("stutt_model_backends.example.json")
MAX_CONFIG_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 128


class ModelBackendError(RuntimeError):
    """Raised when a configured backend is unavailable or returns invalid output."""


def _text(value: Any, field: str, *, nonempty: bool = True) -> None:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ModelBackendError(f"{field} must be a {'nonempty ' if nonempty else ''}string")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ModelBackendError(f"{field} must contain valid Unicode") from None


def _number(value: Any, field: str, *, minimum: float, maximum: float | None = None,
            optional: bool = True, positive: bool = False) -> None:
    if value is None and optional:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or value < minimum or (positive and value == minimum):
        raise ModelBackendError(f"{field} must be a finite {'positive ' if positive else ''}number >= {minimum}")
    if maximum is not None and value > maximum:
        raise ModelBackendError(f"{field} must be <= {maximum}")


def _max_tokens(value: Any) -> None:
    if value is not None and (type(value) is not int or value <= 0):
        raise ModelBackendError("max_tokens must be a positive integer")


def _is_loopback(host: str) -> bool:
    if host.lower().rstrip(".") == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _finite_json_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite JSON number")
    return result


def _check_json_depth(text: str, source: str) -> None:
    """Bound parser nesting while ignoring structural characters in JSON strings."""
    depth = 0
    quoted = False
    escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ModelBackendError(f"{source}: JSON nesting exceeds {MAX_JSON_DEPTH}")
        elif char in "]}":
            depth -= 1


def _decode_json(body: bytes, source: str) -> Any:
    try:
        text = body.decode("utf-8-sig")
        _check_json_depth(text, source)
        return json.loads(text, object_pairs_hook=_json_object,
                          parse_constant=_reject_json_constant, parse_float=_finite_json_float)
    except (ValueError, UnicodeError, RecursionError):
        # Provider errors can echo prompts or credentials; never include the body.
        raise ModelBackendError(f"{source}: invalid UTF-8 JSON") from None


class _RejectRedirects(request.HTTPRedirectHandler):
    """Do not forward prompts or Authorization headers to a redirected endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """A single inference request from STUTT."""

    prompt: str
    context: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        _text(self.prompt, "prompt", nonempty=False)
        if self.context is not None:
            _text(self.context, "context", nonempty=False)
        _max_tokens(self.max_tokens)
        _number(self.temperature, "temperature", minimum=0, maximum=2)
        _number(self.top_p, "top_p", minimum=0, maximum=1)
        _number(self.timeout_seconds, "timeout_seconds", minimum=0, positive=True)


@dataclass(frozen=True, slots=True)
class ModelResult:
    """Observed output from one backend call."""

    content: str
    model: str
    backend: str
    status: int
    raw: Mapping[str, Any] | None = None


class ModelBackend(ABC):
    """Abstract model backend used by STUTT."""

    def __init__(self, name: str, model: str, timeout_seconds: float) -> None:
        self.name = name
        self.model = model
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def infer(self, request_payload: ModelRequest) -> ModelResult:
        """Return one response from this backend."""


@dataclass(frozen=True, slots=True)
class OpenAICompatibleSpec:
    """Configuration fields for OpenAI-compatible endpoints."""

    name: str
    model: str
    base_url: str
    api_key_env: str | None = None
    api_key: str | None = None
    request_path: str = DEFAULT_OPENAI_CHAT_PATH
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        for field in ("name", "model"):
            value = getattr(self, field)
            _text(value, field)
            if any(ord(char) < 32 or ord(char) == 127 for char in value):
                raise ModelBackendError(f"{field} must not contain control characters")
        _max_tokens(self.max_tokens)
        _number(self.temperature, "temperature", minimum=0, maximum=2)
        _number(self.timeout_seconds, "timeout_seconds", minimum=0,
                optional=False, positive=True)
        if self.api_key_env is not None:
            _text(self.api_key_env, "api_key_env")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env):
                raise ModelBackendError("api_key_env must be an environment variable name")
        if self.api_key is not None:
            self._validate_key(self.api_key)
        self.endpoint()

    def endpoint(self) -> str:
        _text(self.base_url, "base_url")
        _text(self.request_path, "request_path")
        for field, value in (("base_url", self.base_url), ("request_path", self.request_path)):
            if any(ord(char) <= 32 or ord(char) >= 127 for char in value) or "\\" in value:
                raise ModelBackendError(f"{field} must be an ASCII URL without whitespace")
        try:
            parts = urlsplit(self.base_url)
            host = parts.hostname
            port = parts.port
            path_parts = urlsplit(self.request_path)
        except ValueError:
            raise ModelBackendError("base_url or request_path is not a valid HTTP endpoint") from None
        if (parts.scheme not in ("http", "https") or not host
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or "?" in self.base_url or "#" in self.base_url
                or port == 0 or "%" in parts.netloc):
            raise ModelBackendError("base_url must be an HTTP(S) URL without credentials, query, or fragment")
        if parts.scheme == "http" and not _is_loopback(host):
            raise ModelBackendError("Non-loopback model endpoints must use HTTPS")
        if (path_parts.scheme or path_parts.netloc or "?" in self.request_path
                or "#" in self.request_path or self.request_path.startswith("//")):
            raise ModelBackendError("request_path must be a path without a host, query, or fragment")
        base = self.base_url.rstrip("/")
        path = self.request_path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"

    def api_key_value(self) -> str | None:
        value = self.api_key if self.api_key is not None else (
            (os.environ.get(self.api_key_env) or None) if self.api_key_env else None
        )
        if value is not None:
            self._validate_key(value)
        return value

    @staticmethod
    def _validate_key(value: Any) -> None:
        _text(value, "API key")
        if any(ord(char) <= 32 or ord(char) >= 127 for char in value):
            raise ModelBackendError("API key must contain printable ASCII without whitespace")


class OpenAICompatibleBackend(ModelBackend):
    """Adapter for OpenAI/NVIDIA-compatible chat-completion endpoints."""

    def __init__(self, spec: OpenAICompatibleSpec) -> None:
        super().__init__(
            name=spec.name,
            model=spec.model,
            timeout_seconds=spec.timeout_seconds,
        )
        self._spec = spec

    @property
    def spec(self) -> OpenAICompatibleSpec:
        """The immutable, validated configuration for backend inspection."""
        return self._spec

    def infer(self, request_payload: ModelRequest) -> ModelResult:
        if not isinstance(request_payload, ModelRequest):
            raise ModelBackendError("request must be a ModelRequest")
        temperature = (
            request_payload.temperature
            if request_payload.temperature is not None
            else self._spec.temperature
        )
        max_tokens = (
            request_payload.max_tokens
            if request_payload.max_tokens is not None
            else self._spec.max_tokens
        )
        timeout_seconds = (
            request_payload.timeout_seconds
            if request_payload.timeout_seconds is not None else self._spec.timeout_seconds
        )
        endpoint = self._spec.endpoint()
        local = _is_loopback(urlsplit(endpoint).hostname or "")
        api_key = self._spec.api_key_value()
        if not api_key and not local:
            raise ModelBackendError(
                f"{self._spec.name}: no API key configured"
            )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        messages = []
        if request_payload.context:
            messages.append(
                {
                    "role": "system",
                    "content": request_payload.context,
                }
            )
        messages.append(
            {
                "role": "user",
                "content": request_payload.prompt,
            }
        )

        payload: dict[str, Any] = {
            "model": self._spec.model,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if request_payload.top_p is not None:
            payload["top_p"] = request_payload.top_p

        try:
            request_bytes = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            req = request.Request(endpoint, data=request_bytes, headers=headers, method="POST")
            handlers = [_RejectRedirects(), request.HTTPSHandler(context=ssl.create_default_context())]
            if local:
                # A configured system proxy must not carry a localhost prompt off-device.
                handlers.append(request.ProxyHandler({}))
            opener = request.build_opener(*handlers)
            with opener.open(req, timeout=timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if type(status) is not int or not 200 <= status < 300:
                    raise ModelBackendError(f"{self._spec.name}: unsuccessful HTTP response")
                raw_body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw_body) > MAX_RESPONSE_BYTES:
                    raise ModelBackendError(f"{self._spec.name}: response exceeds {MAX_RESPONSE_BYTES} bytes")
        except error.HTTPError as exc:
            # Do not read an error body: it is unnecessary and may contain secrets.
            try:
                exc.close()
            except OSError:
                pass
            raise ModelBackendError(f"{self._spec.name}: HTTP {exc.code}") from None
        except TimeoutError:
            raise ModelBackendError(f"{self._spec.name}: request timed out") from None
        except (error.URLError, OSError, HTTPException, ValueError, OverflowError):
            raise ModelBackendError(f"{self._spec.name}: request failed") from None

        raw = _decode_json(raw_body, self._spec.name)

        content = _extract_content(raw)
        if content is None:
            raise ModelBackendError(
                f"{self._spec.name}: no content returned in response"
            )
        _text(content, f"{self._spec.name}: response content", nonempty=False)

        return ModelResult(
            content=content,
            model=self._spec.model,
            backend=self._spec.name,
            status=status,
            raw=raw,
        )


@dataclass(frozen=True, slots=True)
class STUTTModelGateway:
    """Route inference requests through one or more backends."""

    backends: tuple[ModelBackend, ...]
    allow_fallback: bool = False

    def __post_init__(self) -> None:
        if type(self.allow_fallback) is not bool:
            raise ModelBackendError("allow_fallback must be a boolean")

    def infer(self, request_payload: ModelRequest) -> ModelResult:
        if not self.backends:
            raise ModelBackendError("No backend configured")
        last_error: Exception | None = None
        for backend in self.backends:
            try:
                return backend.infer(request_payload)
            except ModelBackendError as exc:
                last_error = exc
                if not self.allow_fallback:
                    raise
        assert last_error is not None
        raise last_error


def _extract_content(raw: Any) -> str | None:
    """Return text content from common OpenAI-style response bodies."""
    if not isinstance(raw, Mapping):
        return None
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    choice0 = choices[0]
    if not isinstance(choice0, Mapping):
        return None

    message = choice0.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if isinstance(content, str):
            return content

    text = choice0.get("text")
    if isinstance(text, str):
        return text
    return None


def load_backends_from_file(path: str | os.PathLike[str] = DEFAULT_CONFIG_PATH) -> list[OpenAICompatibleBackend]:
    """Load and validate UTF-8 JSON; explicit relative paths use the caller's cwd."""
    try:
        config_path = Path(path)
        if not stat.S_ISREG(config_path.stat().st_mode):
            raise ModelBackendError("Model backend configuration must be a regular file")
        with config_path.open("rb") as handle:
            body = handle.read(MAX_CONFIG_BYTES + 1)
    except (OSError, TypeError, ValueError):
        raise ModelBackendError("Cannot read model backend configuration") from None
    if len(body) > MAX_CONFIG_BYTES:
        raise ModelBackendError(f"Model backend configuration exceeds {MAX_CONFIG_BYTES} bytes")
    raw = _decode_json(body, "Model backend configuration")
    if not isinstance(raw, dict) or set(raw) != {"openai_compatible"}:
        raise ModelBackendError("Model configuration must be an object containing only openai_compatible")
    items = raw["openai_compatible"]
    if not isinstance(items, list):
        raise ModelBackendError("openai_compatible must be an array")
    backends = []
    seen = set()
    spec_fields = set(OpenAICompatibleSpec.__dataclass_fields__)
    for index, item in enumerate(items):
        prefix = f"Backend entry {index + 1}"
        if not isinstance(item, dict):
            raise ModelBackendError(f"{prefix} must be an object")
        if set(item) - spec_fields - {"enabled"}:
            raise ModelBackendError(f"{prefix} contains unknown configuration fields")
        if not {"name", "model", "base_url"} <= set(item):
            raise ModelBackendError(f"{prefix} requires name, model, and base_url")
        if type(item.get("enabled", True)) is not bool:
            raise ModelBackendError(f"{prefix}: enabled must be a boolean")
        try:
            spec = OpenAICompatibleSpec(**{key: value for key, value in item.items() if key != "enabled"})
        except ModelBackendError as exc:
            raise ModelBackendError(f"{prefix}: {exc}") from None
        if spec.name in seen:
            raise ModelBackendError(f"{prefix}: duplicate backend name")
        seen.add(spec.name)
        if item.get("enabled", True):
            backends.append(OpenAICompatibleBackend(spec))
    return backends


def build_gateway_from_config(
    *,
    config_path: str | os.PathLike[str] = DEFAULT_CONFIG_PATH,
    backend_name: str | None = None,
    allow_fallback: bool = False,
) -> STUTTModelGateway:
    """Create a reusable gateway from a config file.

    The default example file is resolved beside this module. Prefer environment
    variables for keys. Fallback must be explicitly enabled because it sends the
    same prompt to additional configured providers after an error.
    """
    if backend_name is not None:
        _text(backend_name, "backend_name")
    if type(allow_fallback) is not bool:
        raise ModelBackendError("allow_fallback must be a boolean")
    backends = load_backends_from_file(config_path)
    if not backends:
        raise ModelBackendError(f"No enabled backends in {config_path}")

    if backend_name is None:
        return STUTTModelGateway(
            backends=tuple(backends),
            allow_fallback=allow_fallback,
        )

    named = [backend for backend in backends if backend.name == backend_name]
    if not named:
        raise ModelBackendError(
            f"Backend {backend_name!r} not found in {config_path}"
        )
    ordered = list(named) + [b for b in backends if b.name != backend_name]
    return STUTTModelGateway(
        backends=tuple(ordered),
        allow_fallback=allow_fallback,
    )


def simple_infer(prompt: str, *, context: str | None = None, backend: str | None = None) -> str:
    """Minimal helper for quick command-line exploration.

    This function uses defaults from `stutt_model_backends.example.json`.
    """
    gateway = build_gateway_from_config(backend_name=backend)
    result = gateway.infer(ModelRequest(prompt=prompt, context=context))
    return result.content
