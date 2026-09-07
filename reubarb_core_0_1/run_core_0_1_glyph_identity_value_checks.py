"""I-16: inert glyph-identity value gate check."""
from __future__ import annotations

import sys
import unittest

import test_core_0_1_glyph_identity_value as value_tests


def main() -> int:
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2

    suite = unittest.TestLoader().loadTestsFromTestCase(
        value_tests.GlyphIdentityValueTests
    )
    count = suite.countTestCases()
    print("I-16 gate: inert immutable glyph-identity values", file=sys.stderr)
    print(f"I-16 test count = {count}", file=sys.stderr)
    if count != 16:
        print("Unexpected test inventory; expected exactly 16 for I-16.", file=sys.stderr)
        return 2

    result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(suite)
    if (
        not result.wasSuccessful()
        or result.testsRun != 16
        or result.skipped
        or result.expectedFailures
        or result.unexpectedSuccesses
    ):
        print("I-16 checks did not pass.", file=sys.stderr)
        return 1
    print("I-16 checks passed: 16 of 16.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
