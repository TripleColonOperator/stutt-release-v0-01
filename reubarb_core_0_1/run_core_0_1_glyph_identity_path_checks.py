"""I-20: identity-only native-glyph endpoint acceptance gate."""
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
        import test_core_0_1_glyph_identity_path as endpoint_tests
    except (ImportError, SyntaxError) as exc:
        print(f"I-20 laboratory module could not load: {exc}", file=sys.stderr)
        return 2

    suite = unittest.TestLoader().loadTestsFromTestCase(
        endpoint_tests.GlyphIdentityPathTests
    )
    count = suite.countTestCases()
    print("I-20 gate: identity-only native-glyph endpoint", file=sys.stderr)
    print(f"I-20 test count = {count}", file=sys.stderr)
    if count != 20:
        print("Unexpected test inventory; expected exactly 20 for I-20.", file=sys.stderr)
        return 2

    try:
        result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(suite)
    except KeyboardInterrupt:
        print("I-20 checks interrupted. This run is not a pass.", file=sys.stderr)
        return 130
    if (
        not result.wasSuccessful()
        or result.testsRun != 20
        or result.skipped
        or result.expectedFailures
        or result.unexpectedSuccesses
    ):
        print("I-20 checks did not pass.", file=sys.stderr)
        return 1
    print("I-20 checks passed: 20 of 20.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
