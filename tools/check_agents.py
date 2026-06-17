#!/usr/bin/env python3
"""Agent registry 校验门（CI governance-gates 阻塞项）。

校验 harness/agent-registry.yml 的结构与一致性（stdlib，无需 pyyaml）：
  ① 每个 agent 含 uid/role/model/handles 且非空
  ② role ∈ roles: 段声明的集合
  ③ uid 唯一，且形如 `<role>-NNN`（human 角色为 human-001）
  ④ handles ⊆ requirement-standard §4 生命周期状态
  ⑤ model 非空（human 角色允许 model: human）

退出码：0 全过；1 有失败。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "harness" / "agent-registry.yml"

# 取自 harness/requirement-standard.md §4 生命周期（含 blocked 叠加态）。改生命周期须同步此集。
LIFECYCLE = {
    "draft", "req_review", "tc_design", "tc_review", "tc_impl",
    "tc_impl_review", "req_impl", "req_impl_review", "pr_draft", "done", "blocked",
}


def main() -> int:
    if not REG.exists():
        print(f"✗ 缺 {REG.relative_to(ROOT)}")
        return 1
    text = REG.read_text(encoding="utf-8")
    failures: list[str] = []

    # roles 集合（roles: 与 agents: 之间，形如 "  name: \"...\"")
    roles_block = re.search(r"^roles:[^\n]*\n(.*?)^agents:", text, re.S | re.M)
    roles = set(re.findall(r"^\s{2}([a-z]+):\s", roles_block.group(1), re.M)) if roles_block else set()
    if not roles:
        failures.append("roles: 段为空或缺失")

    # agents 列表：按 "  - uid:" 切块
    agents_block = text.split("\nagents:", 1)[-1]
    blocks = re.split(r"^\s{2}-\s+", agents_block, flags=re.M)[1:]
    seen: set[str] = set()
    if not blocks:
        failures.append("agents: 段无条目")

    for blk in blocks:
        def field(name: str) -> str | None:
            m = re.search(rf"(?:^|\n)\s*{name}:\s*(.+)", blk)
            return m.group(1).strip() if m else None

        uid = field("uid")
        role = field("role")
        model = field("model")
        handles_raw = field("handles")
        tag = uid or "(无 uid)"

        if not uid:
            failures.append("某 agent 缺 uid"); continue
        if uid in seen:
            failures.append(f"{tag}: uid 重复")
        seen.add(uid)
        if not role:
            failures.append(f"{tag}: 缺 role")
        elif roles and role not in roles:
            failures.append(f"{tag}: role '{role}' 未在 roles: 声明")
        if not model:
            failures.append(f"{tag}: 缺 model")
        # uid 命名：<role>-NNN（human 角色为 human-001）
        if role and not re.fullmatch(rf"{re.escape(role)}-\d{{3}}", uid):
            failures.append(f"{tag}: uid 不符 `{role}-NNN` 命名")
        # handles ⊆ 生命周期
        if not handles_raw:
            failures.append(f"{tag}: 缺 handles")
        else:
            handles = re.findall(r"[a-z_]+", handles_raw)
            bad = [h for h in handles if h not in LIFECYCLE]
            if bad:
                failures.append(f"{tag}: handles 含非法生命周期状态 {bad}")

    if failures:
        print("✗ agent-registry 校验失败：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"✓ agent-registry 校验通过（{len(seen)} 个 agent，roles: {sorted(roles)}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
