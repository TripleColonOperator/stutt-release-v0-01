"""I-21 foundation command: I-1 through I-21 fixed gates in sequence."""
from __future__ import annotations

import sys

from run_core_0_1_checks import main as run_i1_to_i21


def main() -> int:
    if len(sys.argv) != 1:
        print("This check takes no arguments.", file=sys.stderr)
        return 2

    print("GART Foundation check: I-1 through I-21 (provisional order)", file=sys.stderr)
    status = run_i1_to_i21()
    if status != 0:
        print(f"I-1 through I-21 did not pass: status={status}", file=sys.stderr)
        return status

    print("Foundation checks passed: I-1 through I-21.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
