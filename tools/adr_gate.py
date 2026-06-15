#!/usr/bin/env python3
"""ADR 评审闭环 gate（CI 必过项）。

实现 harness/adr-standard.md §4.2 的可自动化子集（BUG-006）：
对每个 `status: accepted` 的 ADR 校验——
  ①  informed_by 为空但 Review Notes 非空            → FAIL
  ②  存在悬空裁决（`裁决: pending` / `待裁决`）          → FAIL

§4.1 规则 3「决策一致性 BUG 全闭」依赖人工判定 BUG 性质，暂不自动化，
由评审 + done 门禁（requirement-standard §4）覆盖；此处只锁可机器判定的两条。

退出码：0 全过；1 有失败。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent / "docs" / "adr"


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm: dict[str, str] = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def review_note_bullets(text: str) -> list[str]:
    m = re.search(r"^## Review Notes.*?$(.*)", text, re.S | re.M)
    if not m:
        return []
    return [ln for ln in m.group(1).splitlines() if ln.lstrip().startswith("- [")]


def main() -> int:
    failures: list[str] = []
    checked = 0
    for adr in sorted(ADR_DIR.glob("ADR-*.md")):
        text = adr.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm.get("status") != "accepted":
            continue
        checked += 1
        name = adr.name
        informed_by = fm.get("informed_by", "[]").strip()
        bullets = review_note_bullets(text)

        # ① informed_by 空 + Review Notes 非空
        if bullets and informed_by in ("[]", ""):
            failures.append(f"{name}: accepted 且有 Review Notes，但 informed_by 为空（§4.2①）")

        # ② 悬空裁决：仅匹配显式未决裁决动词（"裁决: pending/待/未"），
        #    不匹配散文里的 "待裁决"（如起草说明列待决问题、其后另有 human-001 裁决 bullet）
        for b in bullets:
            if re.search(r"裁决[:：]\s*(pending|待|未)", b):
                failures.append(f"{name}: 存在悬空/未决裁决条目（§4.2②）：{b.strip()[:60]}…")

    if failures:
        print("✗ ADR gate 失败：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"✓ ADR gate 通过（检查 {checked} 个 accepted ADR）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
