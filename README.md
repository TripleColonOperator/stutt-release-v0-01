# STUTT (Safe Tiered Task/Tool) — Public Beta

STUTT is an experimental command-line prototype with a fixed command allow-list
and optional model-assisted intent routing. Built-in commands run locally without
requiring a model. The optional adapter can connect to separately configured
local or hosted model services.

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
  Example local and NVIDIA cloud backend configurations; endpoint and model
  availability require separate verification.
- `REUBARB_STUTT_ROADMAP.md`  
  Design context and near-term roadmap.
- release metadata:
  - `README.md`, `.gitignore`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`

The full Reubarb language implementation, font/glyph assets, voice interface,
model weights, and model server are not included in this package. The roadmap
also describes work in the larger development workspace.

## How to run

Use Python 3.10 or newer. The command prototype uses the Python standard library;
no package installation or model configuration is needed for the local examples.

From this folder in PowerShell:

```powershell
python .\stutt_command_path.py --input "status"
python .\stutt_command_path.py --input "commands"
python .\stutt_command_path.py --input "count Reubarb has five glyph mappings"
python .\stutt_command_path.py --input "json [1,2,3]"
```

Interactive mode:

```powershell
python .\stutt_command_path.py
```

Type `exit` to stop.

### Optional model mode

Model setup is optional and separate from the quickstart. Configure the endpoint
and model for a service you have running or can access, and set the environment
variable named by `api_key_env` using that service's credentials. Keep literal
`api_key` fields null in any shared configuration. The current adapter requires
a nonempty key value even for a local service.

The example enables both local and cloud entries. In model mode, a failed local
request can fall back to the cloud entry and send the prompt there. For local-only
use, set `enabled` to `false` on every nonlocal entry before enabling model mode.

Once the backend is configured, a free-form request can exercise model routing:

```powershell
python .\stutt_command_path.py --model --input "show the available commands"
```

Recognized commands such as `status` run locally even with `--model`, so their
success does not verify a model connection. Backend failures may return local
help text. Live backend connectivity has not been verified for this release.

## Registered commands

The command registry contains the following entries. See the limitations below
for commands affected by existing bugs or missing development-workspace assets.

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

## Scope and known limitations

Built-in actions do not provide file editing, deletion, or arbitrary shell
execution. Optional model routing can make network requests as described above.
The allow-list is a prototype boundary, not a security certification.

The release cleanup review identified these existing runtime and packaging issues:

- `list-files` currently raises `UnboundLocalError` because its payload is used
  before assignment.
- The local parser lowercases the entire input and strips surrounding whitespace.
  This can alter text, JSON keys/values, and paths. Exact text preservation is not
  currently supported.
- `readme` currently reads `REUBARB_STUTT_ROADMAP.md` instead of `README.md`.
  `roadmap` looks for `Ruebarb Pi.md`, which is not bundled. Open the included
  Markdown files directly to read them.
- `font`, `glyphs`, and `check-glyph-map` refer to development-workspace assets
  absent from this package and report missing files.

These findings are documented for review; this packaging cleanup does not change
runtime behavior or promote any Reubarb language rule.

## Contributing / reporting issues

See `CONTRIBUTING.md` and `SECURITY.md`.

Use issue reports with:

- command used
- expected result
- actual result
- python version / OS
- `--model` enabled or not

## License

MIT License. See [LICENSE](LICENSE).
