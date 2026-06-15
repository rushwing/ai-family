#!/usr/bin/env python3
"""monorepo 布局纪律 gate（CI 必过项）。

实现 ADR-013 / docs/design/07 §5 与 REQ-006 的可机器判定子集：
  ① 必须存在的顶层层目录（apps/agents/toolsets/data/libs/infra/governance/harness/docs）
  ② libs 分层子包齐全（agent-sdk/mcp-contracts/state-schema/auth），且禁止 libs/common
  ③ Agent 之间不得横向 import 彼此 src（只能依赖 libs/ 契约）

REQ-005（依赖图增量 CI）与 REQ-006（import-linter 全量）在其专属 REQ 落地；
此处为 bootstrap 期的轻量结构护栏。退出码：0 过；1 失败。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_DIRS = ["apps", "agents", "toolsets", "data", "libs", "infra", "governance", "harness", "docs"]
LIBS_SUBPKGS = ["agent-sdk", "mcp-contracts", "state-schema", "auth"]


def main() -> int:
    failures: list[str] = []

    # ① 顶层层目录
    for d in REQUIRED_DIRS:
        if not (ROOT / d).is_dir():
            failures.append(f"缺顶层目录 {d}/（07 §5 / ADR-013）")

    # ② libs 分层
    for p in LIBS_SUBPKGS:
        if not (ROOT / "libs" / p).is_dir():
            failures.append(f"缺 libs/{p}/（REQ-006 分层）")
    if (ROOT / "libs" / "common").exists():
        failures.append("禁止 libs/common（REQ-006：契约须分层，不得万能包）")

    # ③ Agent 横向 import 检查
    agents_dir = ROOT / "agents"
    agent_names = [p.name for p in agents_dir.iterdir() if p.is_dir()] if agents_dir.is_dir() else []
    for a in agent_names:
        others = [o for o in agent_names if o != a]
        if not others:
            continue
        pat = re.compile(r"(?:from|import)\s+agents\.(" + "|".join(map(re.escape, others)) + r")\b")
        for py in (agents_dir / a).rglob("*.py"):
            try:
                txt = py.read_text(encoding="utf-8")
            except Exception:
                continue
            m = pat.search(txt)
            if m:
                failures.append(f"{py.relative_to(ROOT)} 横向 import agents.{m.group(1)}（禁；只能依赖 libs/）")

    if failures:
        print("✗ 布局 gate 失败：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("✓ 布局 gate 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
