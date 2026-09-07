"""Combined Core 0.1 checks for I-1 through I-21.

This command delegates to the fixed all-in-one gate.
"""
from __future__ import annotations

import sys

from run_core_0_1_checks import main as run_all_checks


def main() -> int:
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2

    print("Starting combined Core 0.1 gate checks: I-1 through I-21.", file=sys.stderr)
    status = run_all_checks()
    if status != 0:
        print(f"Combined checks did not pass: status={status}", file=sys.stderr)
        return status

    print("Combined checks passed: I-1 through I-21 total 400 tests.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
