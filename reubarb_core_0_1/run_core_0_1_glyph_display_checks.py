"""I-12 dependency-free glyph display-reference checks."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True

_EXACT_FILES = (
    "core_0_1_glyph_display.py",
    "test_core_0_1_glyph_display.py",
    "run_core_0_1_glyph_display_checks.py",
    "reubarb_glyph_encoding_preview.html",
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
        print("One or more fixed I-12 files are missing.", file=sys.stderr)
        return 2
    try:
        before = _snapshot(root)
        import test_core_0_1_glyph_display as i12
    except (OSError, ImportError, SyntaxError):
        print("The fixed I-12 package could not be loaded.", file=sys.stderr)
        return 2
    group = unittest.TestLoader().loadTestsFromTestCase(i12.GlyphDisplayTests)
    if group.countTestCases() != 12:
        print("Unexpected test inventory; expected 12 test(s).", file=sys.stderr)
        return 2
    print("GART I-12 checks: dependency-free glyph display; expected 12 test(s).", file=sys.stderr)
    result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(group)
    try:
        after = _snapshot(root)
    except OSError:
        print("Post-run file verification failed.", file=sys.stderr)
        return 2
    if before != after:
        print("A fixed I-12 file changed during the run.", file=sys.stderr)
        return 2
    if not (
        result.testsRun == 12
        and result.wasSuccessful()
        and not result.skipped
        and not result.expectedFailures
        and not result.unexpectedSuccesses
    ):
        print("I-12 checks not complete.", file=sys.stderr)
        return 1
    print("I-12 checks passed: 12 of 12. The fixed I-12 files are unchanged.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
