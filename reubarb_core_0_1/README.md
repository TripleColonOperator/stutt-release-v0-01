# Reubarb Pi Core 0.1 Foundation

This directory contains the frozen, bounded Core 0.1 Foundation accepted at
gate I-23. It is a reference implementation and contract for public testing and
scrutiny—not the complete Reubarb language.

## Included

- strict UTF-8 transport and source-profile handling;
- lexical records and parser support;
- one `leg` reading instruction for a separately reviewed `textus`;
- five native glyph mappings, canonical SVGs and the Reubarb Pi Symbols font;
- inert glyph identity and bounded occurrence-continuity observations;
- 400 fixed standard-library regression tests;
- the Core 0.1 contract and a 91-file SHA256 freeze inventory.

General literals, bindings, expressions, evaluation, executable `RECON`, Source
machinery and a complete program language remain later work.

## Verify in PowerShell

Requirements: CPython 3.13. From the repository root:

```powershell
Set-Location -LiteralPath .\reubarb_core_0_1
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .\verify_core_0_1_inventory.ps1
if ($LASTEXITCODE -eq 0) {
    py -3.13 -I -B .\run_core_0_1_checks.py
}
```

Expected final messages:

```text
INVENTORY VERIFIED: 91 of 91 files match core-0.1-i23-candidate-1. No files were changed.
CHECKS PASSED: 400 of 400. All fixed gate files are unchanged.
```

The process-only execution-policy argument does not change the machine's saved
PowerShell policy. Review a script before choosing to run it. The checker reads
only the fixed manifest and listed local files; it does not repair anything.

On a platform without the Windows `py` launcher, invoke a real Python 3.13
interpreter directly with `-I -B run_core_0_1_checks.py`.

## Glyphs and font

The font is `fonts/v0_1/ReubarbPiSymbols-Regular.ttf`. The five mappings are:

| Design | Code point | Editor completion |
| --- | --- | --- |
| G2 | U+E100 | `rb.g2` |
| G3 | U+E101 | `rb.g3` |
| G4 | U+E102 | `rb.g4` |
| G5 | U+E103 | `rb.g5` |
| G6 | U+E104 | `rb.g6` |

The completions insert characters in VS Code; they are not Reubarb aliases.
Open `fonts/v0_1/font-preview.html` locally for the font specimen or
`reubarb_glyph_encoding_preview.html` for SVG/encoding references.

The parent STUTT prototype and this frozen language package remain separate.
STUTT's existing `font`, `glyphs`, and `check-glyph-map` commands still inspect
the repository root and do not automatically route into this subdirectory.

## Integrity and limits

`core_0_1_freeze_manifest.json` binds the exact 91-file frozen package. SHA256
detects changes relative to a trusted manifest; it is not a digital signature,
security audit, authorship proof or guarantee that all defects have been found.
Unlisted release files—including this README and the license files—are release
companions and are not part of the frozen runtime inventory.

The BHS PDF, research corpus, private transcripts, machine-specific logs,
credentials, model weights and temporary test environments are not included.

See `CORE_0_1_CONTRACT.md` for the actual bounded guarantee and limitations.

## Licenses

See `LICENSE_SCOPE.md`:

- code and documentation: MIT (`LICENSE-MIT.txt`);
- font and listed glyph artifacts: SIL Open Font License 1.1 (`OFL.txt`);
- build-tool notices: their respective terms in `fonts/v0_1/tool-licenses/`.
