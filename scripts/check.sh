#!/usr/bin/env bash
# scripts/check.sh – 本地运行 CI 治理阻塞门（与 .github/workflows/ci.yml 的 governance-gates 等价）。
# 纯 stdlib，无需 venv。
#
# Usage: ./scripts/check.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

PY="${PYTHON:-python3}"
echo "► ADR 评审闭环 gate（BUG-006 / adr-standard §4.2）"
"$PY" tools/adr_gate.py
echo "► monorepo 布局纪律 gate（ADR-013 / REQ-006）"
"$PY" tools/check_layout.py
echo "► agent registry gate（agent-standard / agent-registry.yml）"
"$PY" tools/check_agents.py
echo "► secret 扫描 gate（BUG-003 ①）"
"$PY" tools/check_secrets.py
echo "► 迁移 RLS 扫描 gate（TC-002-05 / BUG-002）"
"$PY" tools/check_rls.py
echo "✓ 治理门全过"
