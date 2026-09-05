"""First STUTT command path.

This is the first executable command loop:
1) receive user input,
2) interpret intent through local rules (and optional model translation),
3) validate against an allow-list,
4) execute one harmless operation,
5) return a structured result.
"""

from __future__ import annotations

import argparse
import hashlib
import datetime
import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from stutt_model_adapter import (
    ModelBackendError,
    ModelRequest,
    STUTTModelGateway,
    build_gateway_from_config,
)


@dataclass(frozen=True, slots=True)
class CommandDecision:
    action: str
    payload: str | None = None


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    action: str
    allowed: bool
    result: str
    error: str | None = None


ALLOWED_ACTIONS = (
    "status",
    "commands",
    "now",
    "echo",
    "count",
    "trim",
    "reverse",
    "upper",
    "lower",
    "json",
    "font",
    "glyphs",
    "model_backends",
    "list_files",
    "check_glyph_map",
    "env_profile",
    "readme",
    "roadmap",
    "status_overview",
)

COMMAND_ALIASES: Mapping[str, str] = {
    "help": "status",
    "-h": "status",
    "--help": "status",
    "commands": "commands",
    "status": "status",
    "now": "now",
    "echo": "echo",
    "count": "count",
    "stats": "count",
    "trim": "trim",
    "reverse": "reverse",
    "upper": "upper",
    "lower": "lower",
    "json": "json",
    "font": "font",
    "fonts": "font",
    "list-files": "list_files",
    "list_files": "list_files",
    "files": "list_files",
    "dir": "list_files",
    "ls": "list_files",
    "glyph-map": "check_glyph_map",
    "glyphs-map": "check_glyph_map",
    "check-glyph-map": "check_glyph_map",
    "check_glyph_map": "check_glyph_map",
    "check-font": "check_glyph_map",
    "env": "env_profile",
    "env-profile": "env_profile",
    "env_profile": "env_profile",
    "glyphs": "glyphs",
    "glyph": "glyphs",
    "model-backends": "model_backends",
    "model_backends": "model_backends",
    "backends": "model_backends",
    "readme": "readme",
    "roadmap": "roadmap",
    "status-overview": "status_overview",
    "status_overview": "status_overview",
    "overview": "status_overview",
}


def _strip_prefix(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("/"):
        return stripped[1:].strip()
    return stripped


def parse_local_intent(user_input: str) -> CommandDecision | None:
    """Parse command intent without a model."""
    body = _strip_prefix(user_input)
    lowered = body.lower().strip()
    if not lowered:
        return None

    command, sep, remainder = lowered.partition(" ")
    action = COMMAND_ALIASES.get(command)
    if action is None:
        return None

    payload = remainder.strip() if sep else ""
    if action == "status" and command in {"help", "-h", "--help"}:
        payload = "help"
    return CommandDecision(action=action, payload=payload or None)


def build_model_prompt(text: str) -> str:
    return (
        "You are a strict command normalizer for a tiny safe controller.\n"
        "Map user requests to one JSON object and only this JSON shape:\n"
        f'{{"action": one of {tuple(ALLOWED_ACTIONS)}, "payload": "optional text"}}\n'
        "Rules:\n"
        "- action must be in the allow-list.\n"
        "- unknown or unsafe mapping defaults to action=status.\n"
        "- Output only one compact JSON object, no explanation.\n\n"
        f'User request: "{text}"'
    )


def infer_model_decision(
    user_input: str,
    gateway: STUTTModelGateway | None,
) -> CommandDecision | None:
    """Use an optional model gateway to normalize free-form intent."""
    if gateway is None:
        return None

    try:
        raw = gateway.infer(
            ModelRequest(
                prompt=build_model_prompt(user_input),
                context="You are constrained to safe local command routing.",
                max_tokens=220,
                temperature=0.0,
            )
        ).content.strip()
    except ModelBackendError:
        return None

    payload = _extract_json_object(raw)
    if payload is None:
        return None

    action = str(payload.get("action", "")).strip().lower()
    if action not in COMMAND_ALIASES:
        return CommandDecision(action="status")
    action = COMMAND_ALIASES[action]
    value = payload.get("payload")
    if action == "status":
        return CommandDecision(action="status")
    if isinstance(value, str):
        return CommandDecision(action=action, payload=value)
    return CommandDecision(action=action)


def _extract_json_object(raw: str) -> Mapping[str, Any] | None:
    """Attempt to extract one JSON object from noisy model output."""
    candidate = raw.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(line for line in lines if not line.startswith("```")).strip()
    try:
        parsed: Any = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
    return None


def _status_report() -> str:
    return "\n".join(
        [
            "STUTT command path active.",
            "Allowed actions: status, commands, now, echo, count, trim, reverse, upper, lower, json, font, glyphs, model_backends, list_files, check_glyph_map, env_profile, readme, roadmap, status_overview",
            "All actions are local, non-mutating, and allow-list constrained.",
        ]
    )


def _commands_report() -> str:
    return "\n".join(
        [
            "Available commands:",
            "status | commands",
            "now",
            "echo <text>",
            "count <text>",
            "trim <text>",
            "reverse <text>",
            "upper <text>",
            "lower <text>",
            "json <text>",
            "font",
            "glyphs",
            "model-backends",
            "list-files [subdir]",
            "check-glyph-map",
            "env-profile",
            "readme",
            "roadmap",
            "status-overview",
        ]
    )


def _status_overview() -> str:
    return "\n".join(
        [
            "STUTT status overview:",
            "- Foundation contracts: active for reviewed transcript and safe execution boundary.",
            "- Command path: allow-list + optional model normalization.",
            "- Side effects: none.",
            "- Next stage: add controlled permissioned tools on top of this same route.",
        ]
    )


def _safe_now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _read_small_file(file_name: str, max_lines: int = 30) -> str:
    base = Path(__file__).resolve().parent
    target = base / file_name
    if not target.exists():
        return f"File not found: {file_name}"
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return f"Cannot read {file_name}: {exc}"
    content = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        content += "\n..."
    return content


def _action_font() -> str:
    base = Path(__file__).resolve().parent
    font = base / "fonts" / "v0_1" / "ReubarbPiSymbols-Regular.ttf"
    if not font.exists():
        return "Font file not found: fonts\\v0_1\\ReubarbPiSymbols-Regular.ttf"
    try:
        size = font.stat().st_size
    except OSError as exc:
        return f"Font exists but cannot stat: {exc}"
    return f"Font exists: {font.as_posix()} ({size} bytes)"


def _action_glyphs() -> str:
    base = Path(__file__).resolve().parent / "glyphs" / "v0_1"
    if not base.exists():
        return "Glyph directory not found: glyphs\\v0_1"
    files = sorted(p.name for p in base.glob("rp_g*.svg"))
    if not files:
        return "No glyph files found."
    return "\n".join(["Glyph files:"] + files)


def _action_model_backends() -> str:
    base = Path(__file__).resolve().parent
    config = base / "stutt_model_backends.example.json"
    if not config.exists():
        return "Model config not found: stutt_model_backends.example.json"
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except OSError as exc:
        return f"Cannot read model config: {exc}"
    except json.JSONDecodeError as exc:
        return f"Invalid JSON in model config: {exc}"

    if not isinstance(data, Mapping):
        return "Model config has unexpected structure."

    items = []
    for item in data.get("openai_compatible", ()):
        if not isinstance(item, Mapping) or not item.get("enabled", True):
            continue
        name = str(item.get("name", "backend"))
        model = str(item.get("model", ""))
        base_url = str(item.get("base_url", ""))
        request_path = str(item.get("request_path", "/v1/chat/completions"))
        env = item.get("api_key_env")
        has_key = False
        if env and os.environ.get(str(env)):
            has_key = True
        if item.get("api_key"):
            has_key = True
        items.append(
            f"{name} => {model} @ {base_url}{request_path} (key {'present' if has_key else 'missing'})"
        )

    if not items:
        return "Model config has no enabled backends."
    return "\n".join(["Configured model backends:"] + items)


def _action_list_files(payload: str) -> str:
    base = Path(__file__).resolve().parent
    base_root = base
    target = base / payload.strip() if payload.strip() else base
    try:
        target = target.resolve()
        base_root = base_root.resolve()
    except OSError as exc:
        return f"list-files resolution error: {exc}"

    try:
        target.relative_to(base_root)
    except ValueError:
        return "list-files denied: path is outside project"

    if not target.exists():
        return f"list-files: path not found: {payload or '.'}"
    if not target.is_dir():
        return f"list-files: path is not a directory: {payload or '.'}"

    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    if not entries:
        return f"list-files: directory empty ({target.as_posix()})"

    lines = [f"list-files: {target.as_posix()}"]
    for item in entries:
        marker = "/" if item.is_dir() else ""
        lines.append(f"{item.name}{marker}")
    return "\n".join(lines[:220])


def _action_check_glyph_map() -> str:
    base = Path(__file__).resolve().parent
    font = base / "fonts" / "v0_1" / "ReubarbPiSymbols-Regular.ttf"
    manifest_path = base / "fonts" / "v0_1" / "font-manifest.json"
    glyph_dir = base / "glyphs" / "v0_1"
    lines = ["check-glyph-map:"]

    if not font.exists():
        lines.append("font: not found")
    else:
        try:
            font_bytes = font.read_bytes()
            lines.append(f"font: {font.as_posix()}")
            lines.append(f"font_size: {font.stat().st_size} bytes")
            lines.append(f"font_sha256_prefix: {hashlib.sha256(font_bytes).hexdigest()[:20]}")
        except OSError as exc:
            lines.append(f"font read error: {exc}")

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            lines.append(f"manifest parse error: {exc}")
        else:
            glyph_map = manifest.get("glyph_map")
            if isinstance(glyph_map, Mapping):
                lines.append(f"manifest_glyph_count: {len(glyph_map)}")
            else:
                lines.append("manifest_glyph_map: unavailable")
            lines.append(f"manifest_family: {manifest.get('family', 'unknown')}")
    else:
        lines.append("manifest: not found")

    if glyph_dir.exists():
        names = sorted(p.name for p in glyph_dir.glob("*.svg"))
        lines.append(f"glyph_dir_file_count: {len(names)}")
        for name in names[:12]:
            lines.append(f" - {name}")
        if len(names) > 12:
            lines.append(" - ...")
    else:
        lines.append("glyph_dir: not found")

    return "\n".join(lines)


def _action_env_profile() -> str:
    entries = {
        "cwd": os.getcwd(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "os": platform.system(),
    }
    for key in ("NVIDIA_API_KEY", "PYTHONIOENCODING", "PYTHONPATH", "Path"):
        if key in os.environ:
            value = os.environ[key]
            if key == "NVIDIA_API_KEY":
                value = f"<present:{len(value)} chars>"
            elif key == "Path":
                value = f"{len(value.split(os.pathsep))} entries"
            entries[key.lower()] = value
    return "\n".join([f"{key}: {value}" for key, value in entries.items()])


def _safe_json(payload: str) -> str:
    if not payload.strip():
        return "json: expected text input"
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        return f"json parse error: {exc}\ninput: {payload}"
    return json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)


def execute_command(decision: CommandDecision) -> CommandOutcome:
    action = decision.action
    if action not in ALLOWED_ACTIONS:
        return CommandOutcome(
            action=action,
            allowed=False,
            result="",
            error=f"action '{action}' is outside the allow-list",
        )

    if action == "status":
        return CommandOutcome(
            action="status",
            allowed=True,
            result=_status_report() if not decision.payload else _commands_report() if decision.payload == "help" else _status_report(),
        )

    if action == "commands":
        return CommandOutcome(action="commands", allowed=True, result=_commands_report())

    if action == "status_overview":
        return CommandOutcome(action="status_overview", allowed=True, result=_status_overview())

    if action == "now":
        return CommandOutcome(action="now", allowed=True, result=_safe_now())

    if action == "readme":
        return CommandOutcome(action="readme", allowed=True, result=_read_small_file("REUBARB_STUTT_ROADMAP.md", 20))

    if action == "roadmap":
        return CommandOutcome(action="roadmap", allowed=True, result=_read_small_file("Ruebarb Pi.md", 20))

    if action == "font":
        return CommandOutcome(action="font", allowed=True, result=_action_font())

    if action == "glyphs":
        return CommandOutcome(action="glyphs", allowed=True, result=_action_glyphs())

    if action == "model_backends":
        return CommandOutcome(action="model_backends", allowed=True, result=_action_model_backends())

    if action == "list_files":
        return CommandOutcome(action="list_files", allowed=True, result=_action_list_files(payload))

    if action == "check_glyph_map":
        return CommandOutcome(action="check_glyph_map", allowed=True, result=_action_check_glyph_map())

    if action == "env_profile":
        return CommandOutcome(action="env_profile", allowed=True, result=_action_env_profile())

    payload = decision.payload or ""
    if action == "echo":
        return CommandOutcome(action="echo", allowed=True, result=payload)

    if action == "count":
        return CommandOutcome(
            action="count",
            allowed=True,
            result=json.dumps(
                {
                    "characters": len(payload),
                    "words": len(payload.split()),
                    "lines": payload.count("\n") + 1,
                    "text_preview": payload,
                },
                ensure_ascii=False,
            ),
        )

    if action == "trim":
        return CommandOutcome(action="trim", allowed=True, result=payload.strip())

    if action == "reverse":
        return CommandOutcome(action="reverse", allowed=True, result=payload[::-1])

    if action == "upper":
        return CommandOutcome(action="upper", allowed=True, result=payload.upper())

    if action == "lower":
        return CommandOutcome(action="lower", allowed=True, result=payload.lower())

    if action == "json":
        return CommandOutcome(action="json", allowed=True, result=_safe_json(payload))

    return CommandOutcome(
        action=action,
        allowed=False,
        result="",
        error=f"action '{action}' is not implemented",
    )


def run_one(user_input: str, use_model: bool = False, config: str | None = None) -> CommandOutcome:
    clean = user_input.strip()
    if not clean:
        return CommandOutcome(
            action="status",
            allowed=True,
            result="Empty input. Try 'status', 'commands', or 'count example text'.",
        )

    decision = parse_local_intent(clean)
    if decision is None and use_model:
        gateway = None
        if config is None:
            config = "stutt_model_backends.example.json"
        try:
            gateway = build_gateway_from_config(config_path=config)
        except (FileNotFoundError, ModelBackendError):
            gateway = None
        decision = infer_model_decision(clean, gateway)

    if decision is None:
        return CommandOutcome(
            action="status",
            allowed=True,
            result=(
                "No safe command detected. Try:\n"
                "  status\n"
                "  commands\n"
                "  echo <text>\n"
                "  count <text>\n"
                "  model-backends\n"
                "  list-files\n"
                "  check-glyph-map\n"
                "  env-profile"
            ),
        )

    return execute_command(decision)


def run_interactive(use_model: bool = False, config: str | None = None) -> None:
    print("STUTT first command path. Type 'exit' to stop.")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() == "exit":
            break
        outcome = run_one(user_input, use_model=use_model, config=config)
        if outcome.result:
            print(outcome.result)
        if outcome.error:
            print(f"error: {outcome.error}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="STUTT first command path")
    parser.add_argument(
        "--input",
        default=None,
        help="Run one command and exit",
    )
    parser.add_argument(
        "--model",
        action="store_true",
        help="Use the model adapter for intent normalization",
    )
    parser.add_argument(
        "--config",
        default="stutt_model_backends.example.json",
        help="Backend configuration file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    options = parse_args(argv)
    if options.input is not None:
        outcome = run_one(options.input, use_model=options.model, config=options.config)
        if outcome.result:
            print(outcome.result)
        if outcome.error:
            print(f"error: {outcome.error}")
            raise SystemExit(1)
        return
    run_interactive(use_model=options.model, config=options.config)


if __name__ == "__main__":
    main()
