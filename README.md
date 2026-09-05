# STUTT (Safe Tiered Task/Tool) — Public Beta

STUTT is a bounded, open-weight-ready command path prototype. It is designed to
run safe, local, allow-listed commands with optional model-assisted intent routing.

This release is intentionally conservative. It is for review, testing, and
community scrutiny before expanding to broader capabilities.

## What this version includes

- `stutt_command_path.py`  
  First STUTT command path loop:
  - one-shot mode (`--input`)
  - interactive mode
  - command allow-listing
  - optional model-assisted routing (`--model`)
- `stutt_model_adapter.py`  
  Provider abstraction for model backends.
- `stutt_model_backends.example.json`  
  Example backend configuration for NVIDIA/open-weight endpoints.
- `REUBARB_STUTT_ROADMAP.md`  
  Design context and near-term roadmap.
- release metadata:
  - `README.md`, `.gitignore`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`

## How to run

From this folder:

```powershell
python .\stutt_command_path.py --input "status"
python .\stutt_command_path.py --input "commands"
python .\stutt_command_path.py --input "count Reubarb has five glyph mappings"
python .\stutt_command_path.py --input "json {\"hello\": \"world\"}"
```

Interactive mode:

```powershell
python .\stutt_command_path.py
```

Type `exit` to stop.

### Optional model mode

Edit `stutt_model_backends.example.json` with your endpoint values, then set an
environment variable for the key (example for PowerShell):

```powershell
$env:NVIDIA_API_KEY = "your_key_here"
```

Then run:

```powershell
python .\stutt_command_path.py --model --input "status"
```

## Current safe command surface

Available commands:

- `status`
- `commands`
- `now`
- `echo <text>`
- `count <text>`
- `trim <text>`
- `reverse <text>`
- `upper <text>`
- `lower <text>`
- `json <text>`
- `font`
- `glyphs`
- `model-backends`
- `list-files [subdir]`
- `check-glyph-map`
- `env-profile`
- `readme`
- `roadmap`
- `status-overview`

### Scope note

This is a read-only safety-first stage. No file mutation or destructive actions are
enabled yet.

## Contributing / reporting issues

See `CONTRIBUTING.md` and `SECURITY.md`.

Use issue reports with:

- command used
- expected result
- actual result
- python version / OS
- `--model` enabled or not

## License

This project is released under `LICENSE` in this repository.
