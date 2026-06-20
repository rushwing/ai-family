#!/usr/bin/env python3
"""迁移 RLS 扫描门（CI governance-gates 阻塞）—— TC-002-05 / BUG-002 / BUG-014.

扫描 data/migrations/*.sql：
  ① 每个 `CREATE TABLE <t>` 必须有对应 `ALTER TABLE <t> ENABLE ROW LEVEL SECURITY`
     （tenant 隔离默认开；确属非租户表用行内 `-- rls-exempt: <理由>` 豁免）
  ② 禁止 `SECURITY DEFINER`（默认禁，绕过 RLS 风险；例外须人工评审后加 `-- security-definer-ok`）

退出码：0 干净；1 命中。新表无 RLS / 裸 SECURITY DEFINER → 失败。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

MIG = Path(__file__).resolve().parent.parent / "data" / "migrations"
CREATE = re.compile(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([A-Za-z_][\w.]*)", re.I)
ENABLE = re.compile(r"ALTER TABLE\s+([A-Za-z_][\w.]*)\s+ENABLE ROW LEVEL SECURITY", re.I)


def main() -> int:
    failures: list[str] = []
    if not MIG.is_dir():
        print(f"✓ RLS 扫描：无 {MIG.relative_to(MIG.parent.parent)}（跳过）")
        return 0
    for sql in sorted(MIG.glob("*.sql")):
        text = sql.read_text(encoding="utf-8")
        name = sql.name
        created = {m.group(1) for m in CREATE.finditer(text)}
        rls_on = {m.group(1) for m in ENABLE.finditer(text)}
        # 行内豁免：CREATE TABLE 同行含 `-- rls-exempt`
        exempt = set()
        for line in text.splitlines():
            cm = CREATE.search(line)
            if cm and "rls-exempt" in line.lower():
                exempt.add(cm.group(1))
        for t in created - rls_on - exempt:
            failures.append(f"{name}: 表 {t} 未 ENABLE ROW LEVEL SECURITY（① tenant 默认开；非租户表加 -- rls-exempt）")
        # ② SECURITY DEFINER
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"SECURITY\s+DEFINER", line, re.I) and "security-definer-ok" not in line.lower():
                failures.append(f"{name}:{i} 含 SECURITY DEFINER（默认禁；评审通过后加 -- security-definer-ok）")

    if failures:
        print("✗ 迁移 RLS 扫描命中：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("✓ 迁移 RLS 扫描通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
