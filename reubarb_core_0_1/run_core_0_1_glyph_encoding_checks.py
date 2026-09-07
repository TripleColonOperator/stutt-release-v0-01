"""I-10 private-use mapping and workspace-shortcut checks."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True

_EXACT_FILES = (
    "core_0_1_glyph_encoding.py",
    "test_core_0_1_glyph_encoding.py",
    "run_core_0_1_glyph_encoding_checks.py",
    ".vscode/reubarb-glyphs.code-snippets",
)


def _snapshot(root: Path) -> dict[str, str]:
    return {name: sha256((root / name).read_bytes()).hexdigest() for name in _EXACT_FILES}


def main() -> int:
    if sys.version_info[:2] != (3, 13):
        print("Use Python 3.13 for this laboratory check.", file=sys.stderr)
        return 2
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parent
    if any(not (root / name).is_file() for name in _EXACT_FILES):
        print("One or more fixed I-10 files are missing.", file=sys.stderr)
        return 2
    try:
        before = _snapshot(root)
        import test_core_0_1_glyph_encoding as i10
    except (OSError, ImportError, SyntaxError):
        print("The fixed I-10 package could not be loaded.", file=sys.stderr)
        return 2
    group = unittest.TestLoader().loadTestsFromTestCase(i10.GlyphEncodingTests)
    if group.countTestCases() != 14:
        print("Unexpected test inventory; expected 14 test(s).", file=sys.stderr)
        return 2
    print("GART I-10 checks: glyph encoding and shortcuts; expected 14 test(s).", file=sys.stderr)
    result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(group)
    try:
        after = _snapshot(root)
    except OSError:
        print("Post-run file verification failed.", file=sys.stderr)
        return 2
    if before != after:
        print("A fixed I-10 file changed during the run.", file=sys.stderr)
        return 2
    if not (
        result.testsRun == 14
        and result.wasSuccessful()
        and not result.skipped
        and not result.expectedFailures
        and not result.unexpectedSuccesses
    ):
        print("I-10 checks not complete.", file=sys.stderr)
        return 1
    print("I-10 checks passed: 14 of 14. The fixed I-10 files are unchanged.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
