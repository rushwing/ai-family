#!/usr/bin/env python3
"""Reject known household fingerprints and private IPv4 addresses in public assets."""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "apps/home-intelligence-web", ROOT / "docs/product/home-intelligence"]
PATTERNS = {
    "private IPv4 address": re.compile(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"),
    "known household model": re.compile(r"DX4600|X60-PRO|K662c|T30\s*PRO|75Q10G\s*Pro|BCD-501|iPhone\s*17\s*(?:Pro\s*Max|PM)|小米\s*18\s*Fold", re.IGNORECASE),
    "exact household size": re.compile(r"\b(?:154|275)\s*(?:㎡|平(?:方米)?)"),
}
TEXT_SUFFIXES = {".md", ".tsx", ".ts", ".jsx", ".js", ".css", ".json", ".yaml", ".yml", ".html", ".txt"}
XML_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def tracked_files() -> list[Path]:
    command = [
        "git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT),
        "ls-files", "-z", "--", "apps/home-intelligence-web", "docs/product/home-intelligence",
    ]
    result = subprocess.run(command, check=True, capture_output=True)
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def xlsx_strings(path: Path):
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for index, item in enumerate(root.findall("m:si", XML_NS), start=1):
                value = "".join(node.text or "" for node in item.iterfind(".//m:t", XML_NS))
                shared.append(value)
                if value:
                    yield f"xl/sharedStrings.xml#text-{index}", value

        members = [name for name in archive.namelist() if name.startswith("xl/worksheets/") and name.endswith(".xml")]
        for member in members:
            root = ET.fromstring(archive.read(member))
            for cell in root.findall(".//m:c", XML_NS):
                kind = cell.attrib.get("t")
                reference = cell.attrib.get("r", "cell")
                value_node = cell.find("m:v", XML_NS)
                if kind == "inlineStr":
                    value = "".join(node.text or "" for node in cell.iterfind(".//m:t", XML_NS))
                elif kind == "s" and value_node is not None and value_node.text:
                    value = shared[int(value_node.text)]
                elif kind == "str" and value_node is not None:
                    value = value_node.text or ""
                else:
                    value = ""
                if value:
                    yield f"{member}#{reference}", value


def main() -> int:
    failures: list[str] = []
    target_roots = {target.resolve() for target in TARGETS}
    for path in tracked_files():
        if not path.is_file() or not any(root == path.resolve() or root in path.resolve().parents for root in target_roots):
            continue
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() == ".xlsx":
            sources = xlsx_strings(path)
        elif path.suffix.lower() in TEXT_SUFFIXES:
            sources = [("text", path.read_text(encoding="utf-8", errors="ignore"))]
        else:
            continue
        for location, content in sources:
            for label, pattern in PATTERNS.items():
                for match in pattern.finditer(content):
                    line = content.count("\n", 0, match.start()) + 1
                    failures.append(f"{relative}:{location}:{line}: {label}")
    if failures:
        print("Public Home Intelligence data scan failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Public Home Intelligence data scan passed: no known household model, exact home size or private IPv4 address found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
