# Changelog

## v0.1.2-beta - 2026-09-07

### Added

- Publish the frozen Reubarb Pi Core 0.1 Foundation in
  `reubarb_core_0_1/`, including its contract, reference modules, native glyph
  sources, compiled font, previews, 400-test fixed regression suite, and
  91-file SHA256 inventory.
- Add explicit MIT and SIL Open Font License 1.1 scope, the complete OFL text,
  FONTLOG, and retained third-party font-tool notices.
- Add a standalone Core quickstart and integrity-check procedure.

### Verification and limits

- The source freeze inventory and all 400 Foundation tests pass under Python
  3.13.15 on Windows. A clean public-copy verification is run before tagging.
- Core 0.1 is the bounded Foundation, not the complete language. Stage 0.2
  values, bindings, expressions, evaluation, Source machinery, executable
  `RECON`, and broader assistant integration remain future work.
- The existing STUTT command path is not changed by this release. Its asset
  convenience commands do not automatically search the Core subdirectory.
- No BHS PDF, private transcript, credential, model weight, local log, or
  temporary environment is included.

## v0.1.1-beta - 2026-09-05

This beta repairs the standalone STUTT command prototype and makes optional model
routing more explicit. It does not add Reubarb language rules.

### Fixed

- Preserve text, JSON, and path payload case and whitespace after the first
  command delimiter; command words remain case-insensitive.
- Fix the `list-files` crash and point `readme` and `roadmap` at bundled files.
- Count CR, LF, and CRLF line endings consistently and mark truncated glyph
  inventories instead of displaying capped counts as complete totals.
- Validate model decisions, backend configuration, and model responses before
  using them; report expected configuration, request, and CLI errors.
- Resolve the default backend configuration beside the module and respect
  configured request timeouts.
- Handle end-of-input and Ctrl+C cleanly. Bound command input and local text
  reads, and reject invalid, ambiguous, or excessively nested JSON.

### Changed

- Backend fallback is opt-in through `--model-fallback`; the cloud example is
  disabled by default. The local example supports a service without an API key.
- Refresh the disabled NVIDIA example and require users to match service URLs,
  model identifiers, and credentials to their deployment.
- Add offline regression tests, reproducible quickstart/test instructions,
  personal configuration ignore rules, and private security-reporting guidance.

### Verification and remaining limits

Local verification on Windows with Python 3.13.15: 96 tests discovered,
95 passed, and one native directory-symlink test skipped because the operating
system did not permit symlink creation. Mocked resolved-symlink boundary tests
passed. The suite includes subprocess checks against a copied standalone
package launched from another working directory.

Run the standard-library regression suite from the release folder:

```powershell
python -B -m unittest discover -s tests -v
```

Model requests in these tests are mocked. No live model service, NVIDIA GPU,
model download, or inference performance was tested. Passing these tests is not
a security audit or a claim that every defect has been found.

Python 3.10 is the minimum supported syntax/API target; only Python 3.13.15 on
Windows was executed for this local verification. HTTP timeouts bound blocking
operations, not an absolute end-to-end wall-clock deadline.

This package does not include a finished Reubarb language, glyph/font assets,
voice interface, model weights, or inference server. The related asset commands
report missing files. Optional model mode can send input to configured network
services, including additional enabled services when fallback is requested.
