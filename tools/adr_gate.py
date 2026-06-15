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

        # ② 逐「意见」bullet 校验裁决（BUG-027/BUG-028，adr-standard §4.1 规则 2）：
        #    每条 reviewer（codex-*/gemini-*）意见都必须带 human-001 终裁。
        #    - pending / 待裁决            → FAIL（悬空）
        #    - 无任何非-pending 的「裁决：」 → FAIL（普通未裁决意见）
        #    - 裁决为 defer 但缺 Revisit Trigger → FAIL
        #    claude*/human-001 等记录/裁决类 bullet 非「意见」，豁免。
        PENDING = r"裁决[:：]\s*(pending|待定|未定|待|未)"
        # 真实终裁必须是 human-001 的非-pending 裁决（标准 §4.1 规则2：每条意见带 human-001 裁决）；
        # 仅有 "Claude 裁决：accept" 之类非人裁决不算（BUG-029）。
        RULING = r"human-001\s*裁决[:：]\s*(?!pending|待定|未定|待|未)\S"
        for b in bullets:
            um = re.match(r"-\s*\[([^\]]+)\]", b)
            uid = um.group(1) if um else ""
            if not (uid.startswith("codex") or uid.startswith("gemini")):
                continue  # 非 reviewer 意见（记录/裁决/对齐），豁免
            short = b.strip()[:64]
            if "待裁决" in b or re.search(PENDING, b):
                failures.append(f"{name}: reviewer 意见悬空未裁（pending/待裁决，§4.1②）：{short}…")
            elif not re.search(RULING, b):
                failures.append(f"{name}: reviewer 意见缺 human-001 裁决（§4.1②）：{short}…")
            elif re.search(r"裁决[:：]\s*\**defer", b) and not re.search(r"Revisit", b):
                failures.append(f"{name}: defer 裁决缺 Revisit Trigger（§4.1②）：{short}…")

    if failures:
        print("✗ ADR gate 失败：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"✓ ADR gate 通过（检查 {checked} 个 accepted ADR）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
