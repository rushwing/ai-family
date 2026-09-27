#!/usr/bin/env python3
"""Reject known household fingerprints and private IPv4 addresses in public assets."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "apps/home-intelligence-web", ROOT / "docs/product/home-intelligence"]
SKIP = {"requirements.xlsx"}
PATTERNS = {
    "private IPv4 address": re.compile(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"),
    "known household model": re.compile(r"DX4600|X60-PRO|K662c|T30\s*PRO|75Q10G\s*Pro|BCD-501|iPhone\s*17\s*(?:Pro\s*Max|PM)|小米\s*18\s*Fold", re.IGNORECASE),
    "exact household size": re.compile(r"\b(?:154|275)\s*㎡"),
}
TEXT_SUFFIXES = {".md", ".tsx", ".ts", ".jsx", ".js", ".css", ".json", ".yaml", ".yml", ".html", ".txt"}
IGNORED_PARTS = {"node_modules", ".next", "dist", ".wrangler"}


def main() -> int:
    failures: list[str] = []
    for target in TARGETS:
        for path in target.rglob("*"):
            if not path.is_file() or path.name in SKIP or path.suffix.lower() not in TEXT_SUFFIXES or IGNORED_PARTS.intersection(path.parts):
                continue
            relative = path.relative_to(ROOT).as_posix()
            if "/private/" in f"/{relative}/" or "REVIEW-PR21.md" in relative:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in PATTERNS.items():
                for match in pattern.finditer(content):
                    line = content.count("\n", 0, match.start()) + 1
                    failures.append(f"{relative}:{line}: {label}")
    if failures:
        print("Public Home Intelligence data scan failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Public Home Intelligence data scan passed: no known household model, exact home size or private IPv4 address found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
