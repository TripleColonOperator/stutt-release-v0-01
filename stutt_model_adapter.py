"""Model backend abstraction for STUTT.

The language layer remains separate from reasoning model execution.
This module intentionally provides a narrow interface so new providers can be
added without changing STUTT control flow.
"""

from __future__ import annotations

import json
import os
import ssl
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib import error, request


DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_OPENAI_CHAT_PATH = "/v1/chat/completions"


class ModelBackendError(RuntimeError):
    """Raised when a configured backend is unavailable or returns invalid output."""


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """A single inference request from STUTT."""

    prompt: str
    context: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS


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

    def endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        path = self.request_path.strip()
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"

    def api_key_value(self) -> str | None:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.environ.get(self.api_key_env)
        return None


class OpenAICompatibleBackend(ModelBackend):
    """Adapter for OpenAI/NVIDIA-compatible chat-completion endpoints."""

    def __init__(self, spec: OpenAICompatibleSpec) -> None:
        super().__init__(
            name=spec.name,
            model=spec.model,
            timeout_seconds=spec.timeout_seconds,
        )
        self._spec = spec

    def infer(self, request_payload: ModelRequest) -> ModelResult:
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
            request_payload.timeout_seconds or self._spec.timeout_seconds
        )
        api_key = self._spec.api_key_value()
        if not api_key:
            raise ModelBackendError(
                f"{self._spec.name}: no API key configured"
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
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

        request_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self._spec.endpoint(),
            data=request_bytes,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(
                req,
                timeout=timeout_seconds,
                context=ssl.create_default_context(),
            ) as response:
                raw_body = response.read().decode("utf-8")
                status = getattr(response, "status", 200)
        except error.HTTPError as exc:
            status = exc.code
            raw_body = exc.read().decode("utf-8", errors="ignore")
            raise ModelBackendError(
                f"{self._spec.name}: HTTP {status} -> {raw_body}"
            )
        except error.URLError as exc:
            raise ModelBackendError(f"{self._spec.name}: request failed: {exc}") from exc

        try:
            raw = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ModelBackendError(
                f"{self._spec.name}: invalid JSON response: {raw_body}"
            ) from exc

        content = _extract_content(raw)
        if content is None:
            raise ModelBackendError(
                f"{self._spec.name}: no content returned in response"
            )

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
    allow_fallback: bool = True

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


def _extract_content(raw: Mapping[str, Any]) -> str | None:
    """Return text content from common OpenAI-style response bodies."""
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


def load_backends_from_file(path: str | os.PathLike[str] = "stutt_model_backends.example.json") -> list[OpenAICompatibleBackend]:
    """Load backend specs from a JSON file."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    return [
        OpenAICompatibleBackend(
            OpenAICompatibleSpec(
                name=item["name"],
                model=item["model"],
                base_url=item["base_url"],
                api_key_env=item.get("api_key_env"),
                api_key=item.get("api_key"),
                request_path=item.get("request_path", DEFAULT_OPENAI_CHAT_PATH),
                temperature=item.get("temperature"),
                max_tokens=item.get("max_tokens"),
                timeout_seconds=item.get("timeout_seconds", DEFAULT_REQUEST_TIMEOUT_SECONDS),
            )
        )
        for item in raw.get("openai_compatible", ())
        if item.get("enabled", True)
    ]


def build_gateway_from_config(
    *,
    config_path: str | os.PathLike[str] = "stutt_model_backends.example.json",
    backend_name: str | None = None,
    allow_fallback: bool = True,
) -> STUTTModelGateway:
    """Create a reusable gateway from a config file.

    The `config_path` defaults to the included example file. Point this to your own
    local file once keys are copied from your secrets source.
    """
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
