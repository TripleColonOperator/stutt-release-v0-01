"""I-8 (native-glyph technical profile) fixed laboratory checks.

No transcript input, no path discovery, no source-file loading, and no
runtime side effects beyond deterministic test execution.
"""
from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path
import unittest

sys.dont_write_bytecode = True

_EXACT_FILES = (
    "core_0_1_glyph_technical.py",
    "test_core_0_1_glyph_technical.py",
)


def _snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in _EXACT_FILES:
        digest = sha256()
        with (root / name).open("rb") as source:
            while chunk := source.read(65536):
                digest.update(chunk)
        result[name] = digest.hexdigest()
    return result


def main() -> int:
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    missing = tuple(name for name in _EXACT_FILES if not (root / name).is_file())
    if missing:
        print("Keep these files beside this runner: " + ", ".join(missing), file=sys.stderr)
        return 2

    try:
        before = _snapshot(root)
    except OSError:
        print("Could not hash required files. Nothing was rewritten.", file=sys.stderr)
        return 2

    try:
        import test_core_0_1_glyph_technical as i1
    except (ImportError, SyntaxError):
        print("A named laboratory module could not load. Check the two gate files.", file=sys.stderr)
        return 2

    loader = unittest.TestLoader()
    group = loader.loadTestsFromTestCase(i1.GlyphTechnicalTests)
    if group.countTestCases() != 8:
        print("Unexpected test inventory; expected 8 test(s). Stopped.", file=sys.stderr)
        return 2

    print("GART I-8 checks: Native-glyph technical profile; expected 8 test(s).", file=sys.stderr)
    result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(unittest.TestSuite((group,)))

    try:
        after = _snapshot(root)
    except OSError:
        print("Post-run file verification failed. This run is not accepted as a pass.", file=sys.stderr)
        return 2

    if before != after:
        print("A named code file changed during the run. Stop and review; no rollback was run.", file=sys.stderr)
        return 2

    if not (
        result.testsRun == 8
        and result.wasSuccessful()
        and not result.skipped
        and not result.expectedFailures
        and not result.unexpectedSuccesses
    ):
        print("I-8 checks not complete. Review the test output.", file=sys.stderr)
        return 1

    print("I-8 checks passed: 8 of 8. The gate files are unchanged.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
