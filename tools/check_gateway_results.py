#!/usr/bin/env python3
"""Reject absent/skipped shared prerequisite suites in the MCP CI report."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main(path: str) -> int:
    cases = list(ET.parse(Path(path)).iter("testcase"))
    for module in ("test_confirmation_pg", "test_registered_home"):
        selected = [c for c in cases if c.get("classname", "").endswith(module)]
        if not selected or any(c.find(tag) is not None for c in selected
                               for tag in ("skipped", "failure", "error")):
            print(f"Required shared gateway suite missing or not passing: {module}")
            return 1
    print("Shared gateway prerequisites executed with zero skipped or failing cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
