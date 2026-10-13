"""One deterministic JSON line per complete offline demonstration scenario."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import NoReturn

from .caller import canonical_json, run_demo
from .scenarios import DemoError


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse's default diagnostics echo user-supplied arguments.
        self.exit(2, "demo: unsupported arguments\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(description="Deterministic fictional device scenario verification",
                     allow_abbrev=False)
    parser.add_argument("--device", required=True)
    parser.add_argument("--scenario", required=True)
    args = parser.parse_args(argv)
    try:
        output = canonical_json(run_demo(args.device, args.scenario))
    except DemoError as error:
        if error.code == "unsupported_scenario":
            sys.stderr.write("demo: unsupported device/scenario\n")
            return 2
        sys.stderr.write("demo: scenario verification failed\n")
        return 1
    except Exception:
        # Keep CLI diagnostics value-free; call run_demo directly for a debugging traceback.
        sys.stderr.write("demo: internal execution failed\n")
        return 1
    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
