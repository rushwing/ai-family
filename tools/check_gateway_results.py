#!/usr/bin/env python3
"""Require every pinned prerequisite case exactly once and passing in JUnit."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED = json.loads(Path(__file__).with_name("gateway_required_cases.json").read_text())


def main(path: str) -> int:
    try:
        cases = list(ET.parse(Path(path)).iter("testcase"))
    except (OSError, ET.ParseError):
        print("Required shared gateway report missing or invalid")
        return 1
    for module, names in REQUIRED.items():
        selected = [c for c in cases if c.get("classname", "").split(".")[-1] == module]
        for name in names:
            matches = [c for c in selected if c.get("name") == name]
            if len(matches) != 1:
                print(f"Required shared gateway case missing or duplicated: {module}.{name}")
                return 1
        if any(
            c.find(tag) is not None for c in selected for tag in ("skipped", "failure", "error")
        ):
            print(f"Required shared gateway suite not passing: {module}")
            return 1
    print("Shared gateway prerequisites executed with zero skipped or failing cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
