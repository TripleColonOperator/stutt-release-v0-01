"""I-15: native-glyph source-integration gate check."""
from __future__ import annotations

import sys
import unittest

import test_core_0_1_glyph_source_integration as integration_tests


def main() -> int:
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2

    suite = unittest.TestLoader().loadTestsFromTestCase(
        integration_tests.GlyphSourceIntegrationTests
    )
    count = suite.countTestCases()
    print("I-15 gate: accepted native-glyph source integration", file=sys.stderr)
    print(f"I-15 test count = {count}", file=sys.stderr)
    if count != 11:
        print("Unexpected test inventory; expected exactly 11 for I-15.", file=sys.stderr)
        return 2

    result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(suite)
    if not result.wasSuccessful() or result.testsRun != 11 or result.skipped:
        print("I-15 checks did not pass.", file=sys.stderr)
        return 1
    print("I-15 checks passed: 11 of 11.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
