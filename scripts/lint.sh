#!/usr/bin/env bash
# scripts/lint.sh – 仓库级 ruff（根 pyproject 配置；agents/goal 沿用其自带配置，已 extend-exclude）。
#
# Usage:
#   ./scripts/lint.sh          # 检查
#   ./scripts/lint.sh --fix    # 自动修复
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

FIX=false
for arg in "$@"; do [[ "$arg" == "--fix" ]] && FIX=true; done

# 优先用仓库级 .venv 的 ruff；否则回退 uvx（uv tool 运行，无需预装）
if [[ -x ".venv/bin/ruff" ]]; then
  RUFF=(.venv/bin/ruff)
elif command -v uvx &>/dev/null; then
  RUFF=(uvx ruff)
else
  echo "✗ 未找到 ruff。先跑 ./scripts/setup.sh，或安装 uv。"; exit 1
fi

if $FIX; then
  echo "► ${RUFF[*]} check --fix ."
  "${RUFF[@]}" check --fix .
  "${RUFF[@]}" format .
else
  echo "► ${RUFF[*]} check ."
  "${RUFF[@]}" check .
fi
