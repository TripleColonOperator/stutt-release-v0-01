"""I-21: fixed reviewed-text end-to-end demonstration gate."""
from __future__ import annotations

import sys
import unittest


def main() -> int:
    if sys.version_info[:2] != (3, 13):
        print(
            "Use Python 3.13 for this laboratory check. No installation was attempted.",
            file=sys.stderr,
        )
        return 2
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2

    try:
        import test_core_0_1_reviewed_text_path as path_tests
    except (ImportError, SyntaxError) as exc:
        print(f"I-21 laboratory module could not load: {exc}", file=sys.stderr)
        return 2

    suite = unittest.TestLoader().loadTestsFromTestCase(
        path_tests.ReviewedTextPathTests
    )
    count = suite.countTestCases()
    print("I-21 gate: fixed reviewed-text end-to-end demonstration", file=sys.stderr)
    print(f"I-21 test count = {count}", file=sys.stderr)
    if count != 12:
        print("Unexpected test inventory; expected exactly 12 for I-21.", file=sys.stderr)
        return 2

    try:
        result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(suite)
    except KeyboardInterrupt:
        print("I-21 checks interrupted. This run is not a pass.", file=sys.stderr)
        return 130
    if (
        not result.wasSuccessful()
        or result.testsRun != 12
        or result.skipped
        or result.expectedFailures
        or result.unexpectedSuccesses
    ):
        print("I-21 checks did not pass.", file=sys.stderr)
        return 1
    print("I-21 checks passed: 12 of 12.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
