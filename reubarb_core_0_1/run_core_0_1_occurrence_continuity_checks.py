"""I-18: inert exact-anchor same-occurrence continuity gate check."""
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
        import test_core_0_1_occurrence_continuity as continuity_tests
    except (ImportError, SyntaxError) as exc:
        print(f"I-18 laboratory module could not load: {exc}", file=sys.stderr)
        return 2

    suite = unittest.TestLoader().loadTestsFromTestCase(
        continuity_tests.OccurrenceContinuityTests
    )
    count = suite.countTestCases()
    print("I-18 gate: inert exact-anchor occurrence continuity", file=sys.stderr)
    print(f"I-18 test count = {count}", file=sys.stderr)
    if count != 18:
        print("Unexpected test inventory; expected exactly 18 for I-18.", file=sys.stderr)
        return 2

    result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(suite)
    if (
        not result.wasSuccessful()
        or result.testsRun != 18
        or result.skipped
        or result.expectedFailures
        or result.unexpectedSuccesses
    ):
        print("I-18 checks did not pass.", file=sys.stderr)
        return 1
    print("I-18 checks passed: 18 of 18.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
