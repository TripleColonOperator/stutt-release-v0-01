# STUTT (Safe Tiered Task/Tool) — Public Beta

STUTT is an experimental command-line prototype with a fixed command allow-list
and optional model-assisted intent routing. Built-in commands run locally without
requiring a model. The optional adapter can connect to separately configured
local or hosted model services.

Version: `v0.1.1-beta`. This release is for review, testing, and community scrutiny
before expanding to broader capabilities. See [CHANGELOG.md](CHANGELOG.md) for
the beta fixes and verification limits.

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
  Example local backend and a disabled NVIDIA cloud entry. Match the endpoint
  and model identifier to a service you can access.
- `tests/`
  Standard-library regression tests with mocked model requests.
- `REUBARB_STUTT_ROADMAP.md`
  Design context and near-term roadmap.
- release metadata:
  - `README.md`, `CHANGELOG.md`, `.gitignore`, `LICENSE`, `CONTRIBUTING.md`,
    `SECURITY.md`

The full Reubarb language implementation, font/glyph assets, voice interface,
model weights, and model server are not included in this package. The roadmap
also describes work in the larger development workspace.

## How to run

Use Python 3.10 or newer. The command prototype uses the Python standard library;
no package installation or model configuration is needed for the local examples.

From this folder in PowerShell:

```powershell
python -B .\stutt_command_path.py --input "status"
python -B .\stutt_command_path.py --input "commands"
python -B .\stutt_command_path.py --input "echo Hello, STUTT"
python -B .\stutt_command_path.py --input "count Sample text"
python -B .\stutt_command_path.py --input "json [1,2,3]"
python -B .\stutt_command_path.py --input "list-files"
```

Interactive mode:

```powershell
python -B .\stutt_command_path.py
```

Type `exit` to stop. End-of-input also exits normally; Ctrl+C exits with status
130. A failed one-shot command exits with status 1 and an error message.

Command words are case-insensitive. Text after the first separating whitespace
character keeps its original case and remaining whitespace. For example,
`echo Hello` returns `Hello`; `trim`, `upper`, and `lower` change text explicitly.

### Run the tests

From the release folder:

```powershell
python -B -m unittest discover -s tests -v
```

These are offline regression tests. Model requests are mocked; passing tests
does not establish live backend, NVIDIA GPU, or inference performance support.

### Optional model mode

Model setup is optional and separate from the quickstart. Copy the example to a
personal configuration file:

```powershell
Copy-Item .\stutt_model_backends.example.json .\stutt_model_backends.local.json
```

Edit that copy to match your running service's `base_url`, `request_path`, and
`model`. Replace `your-local-model-id` with the model identifier your server
actually serves; the example does not install or start a model. The local
example uses `http://localhost:8000` and permits a service without an API key.
Non-loopback endpoints require a key in this adapter. For authentication, set
`api_key_env` to the name of an environment variable containing your key. Keep
literal `api_key` fields null in shared files. `stutt_model_backends.local.json`
is ignored by Git.

The adapter sends nonstreaming OpenAI-compatible chat-completion requests. It
requires HTTPS for remote services; plain HTTP is limited to loopback
addresses such as localhost. Redirects are rejected, and loopback requests
bypass environment proxy settings.

The first enabled backend is used; fallback is off by default. The NVIDIA cloud
example is disabled. To use it, configure credentials and a model supported by
that service, enable the cloud entry, and disable or reorder any earlier entry
as appropriate. Selecting a remote endpoint sends model-routing input and its
routing context to that endpoint.

The disabled cloud example follows [NVIDIA's documented Nemotron endpoint](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b-infer).
Account access and live availability still need verification with your service.

Once your backend is configured, exercise model routing with an unrecognized
free-form request:

```powershell
python -B .\stutt_command_path.py --model --config .\stutt_model_backends.local.json --input "show the available commands"
```

Use `--model-fallback` only when you want failed model requests to try the next
enabled backend. This can send the same input to another service, including a
cloud service if you have enabled one. For local-only use, keep every remote
entry disabled. If `--config` is omitted, the bundled example beside the script
is used, even when you launch the script from another directory.

Recognized commands such as `status` run locally even with `--model`, so their
success does not verify a model connection. Invalid model output or backend
failures produce an error without executing a proposed action. No live backend
connection, model download, or GPU execution was verified for this release.

## Registered commands

The command registry contains the following entries. Glyph and font commands
report missing assets in this standalone package, as described below.

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

- `font`, `glyphs`, and `check-glyph-map` refer to development-workspace assets
  absent from this package and report missing files. No font installation or
  glyph rendering is provided.
- There is no finished Reubarb language, voice interface, model training,
  bundled model weights, or inference server in this release.
- NVIDIA and open-weight model integration means a configurable compatible
  endpoint. It does not imply a tested NVIDIA deployment or built-in GPU support.
- Command input is limited to 65,536 Unicode characters. Local document and
  configuration reads are limited to 1 MiB. JSON helpers reject duplicate keys,
  nonstandard `NaN`/`Infinity` values, numbers outside the host's finite float
  range, and nesting beyond 128 containers. JSON numbers use Python's integer
  and floating-point representations; this is not an exact-decimal calculator.
  JSON is transport and configuration, not the Reubarb language definition.
- Regression tests cover the repaired paths; they are not a comprehensive
  security audit or a promise that every defect has been found.
- File-boundary checks operate within this process. They do not isolate the
  program from another local process modifying files or links concurrently.
  Backend timeouts apply to blocking operations, not an absolute overall deadline.

These are host-prototype fixes and limits; they do not adopt new Reubarb language
rules.

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
