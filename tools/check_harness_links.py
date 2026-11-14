"""Check inline local links in active Harness requirements against tracked files."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def broken_links(root: Path, source: Path, tracked: set[Path]) -> list[str]:
    errors = []
    for target in re.findall(r"\[[^\]\n]+\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            continue
        destination = (source.parent / unquote(target.split("#", 1)[0])).resolve()
        if not destination.is_relative_to(root.resolve()) or not (
            destination in tracked
            or (destination.is_dir() and any(p.is_relative_to(destination) for p in tracked))
        ):
            errors.append(f"{source.relative_to(root)} -> {target}")
    return errors


def main() -> int:
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    tracked = {(ROOT / p).resolve() for p in paths if p}
    sources = sorted(
        p for p in tracked
        if p.parent == ROOT / "harness/tasks/features" and p.suffix == ".md"
    )
    errors = [error for p in sources for error in broken_links(ROOT, p, tracked)]
    for error in errors:
        print(f"Broken or untracked Harness link: {error}")
    if not errors:
        print(f"Active Harness links passed ({len(sources)} requirements).")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
