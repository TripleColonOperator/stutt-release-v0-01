# Contributing

This public beta is a small Python command prototype. Keep changes focused and
include a regression test when fixing command behavior or model integration.
Changes to the future Reubarb language need a separate design proposal; this
package does not define its grammar or semantics.

Use Python 3.10 or newer. From the release folder, run:

```powershell
python -B -m unittest discover -s tests -v
```

The regression suite uses the standard library and mocks model requests. It
should not require credentials, model weights, a GPU, or a network connection.
Record your Python version, operating system, test command, and results in a
pull request. Explain the observed bug and what the change makes happen instead.

For a normal bug report, include:

- The exact command and a minimal, sanitized input.
- The expected and actual results.
- Python version and operating system.
- Whether `--model`, `--config`, or `--model-fallback` was used.
- For model issues, the backend type and a sanitized error, without credentials
  or private prompts.

Keep personal backend configuration in `stutt_model_backends.local.json`, which
is ignored by Git. Keep credentials in environment variables. Check the files
and diff before committing; ignore rules do not protect already tracked files.
Do not submit API keys, private transcripts, logs, or model weights.

For suspected vulnerabilities, follow [SECURITY.md](SECURITY.md).
