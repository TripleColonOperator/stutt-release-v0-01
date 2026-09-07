"""I-9 approved-glyph visual-geometry checks; finite and foreground only."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True

_EXACT_FILES = (
    "core_0_1_glyph_geometry.py",
    "test_core_0_1_glyph_geometry.py",
    "run_core_0_1_glyph_geometry_checks.py",
    "glyphs/v0_1/rp_component_four_dot_frame.svg",
    "glyphs/v0_1/rp_g02_congruent_statement.svg",
    "glyphs/v0_1/rp_g03_fulfilled_overlay.svg",
    "glyphs/v0_1/rp_g04_strong_variant.svg",
    "glyphs/v0_1/rp_g05_neutral_variant.svg",
    "glyphs/v0_1/rp_g06_weak_variant.svg",
)


def _snapshot(root: Path) -> dict[str, str]:
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in _EXACT_FILES
    }


def main() -> int:
    if sys.version_info[:2] != (3, 13):
        print("Use Python 3.13 for this laboratory check.", file=sys.stderr)
        return 2
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    if any(not (root / name).is_file() for name in _EXACT_FILES):
        print("One or more fixed I-9 files are missing.", file=sys.stderr)
        return 2

    try:
        before = _snapshot(root)
        import test_core_0_1_glyph_geometry as i9
    except (OSError, ImportError, SyntaxError):
        print("The fixed I-9 package could not be loaded.", file=sys.stderr)
        return 2

    group = unittest.TestLoader().loadTestsFromTestCase(i9.GlyphGeometryTests)
    if group.countTestCases() != 12:
        print("Unexpected test inventory; expected 12 test(s).", file=sys.stderr)
        return 2

    print("GART I-9 checks: approved native-glyph geometry; expected 12 test(s).", file=sys.stderr)
    result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(group)

    try:
        after = _snapshot(root)
    except OSError:
        print("Post-run file verification failed.", file=sys.stderr)
        return 2
    if before != after:
        print("A fixed I-9 file changed during the run.", file=sys.stderr)
        return 2
    if not (
        result.testsRun == 12
        and result.wasSuccessful()
        and not result.skipped
        and not result.expectedFailures
        and not result.unexpectedSuccesses
    ):
        print("I-9 checks not complete.", file=sys.stderr)
        return 1

    print("I-9 checks passed: 12 of 12. The fixed I-9 files are unchanged.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
