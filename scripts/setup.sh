#!/usr/bin/env bash
# scripts/setup.sh – 初始化 ai-family 仓库级开发环境（uv 管理）。
#
# 仓库级 .venv 仅装“治理/lint 工具”（ruff 等）；各模块（agents/<name>、toolsets/mcp/<server>、
# libs/<pkg>）有各自 pyproject + 依赖，按需 `cd <module> && uv sync --extra dev`
# （goal-agent 见 agents/goal/scripts/setup.sh）。
#
# Usage: ./scripts/setup.sh
# 要求：uv（https://docs.astral.sh/uv/）— 缺失则自动安装。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

# ── 1. 确保 uv 可用 ──────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  echo "► uv 未安装 — 用官方脚本安装…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "► uv $(uv --version)"

# ── 2. 仓库级 venv + 治理/lint 工具 ──────────────────────────────
echo "► 创建仓库级 .venv（Python 3.12）…"
uv venv --python 3.12 .venv
echo "► 安装仓库级开发工具（ruff）…"
uv pip install --python .venv/bin/python ruff

echo ""
echo "✓ 仓库级环境就绪。"
echo "  激活        : source .venv/bin/activate"
echo "  治理门      : ./scripts/check.sh   （ADR gate + 布局 gate，同 CI）"
echo "  lint        : ./scripts/lint.sh [--fix]"
echo "  模块测试    : ./scripts/test.sh <module>"
echo "  goal-agent  : cd agents/goal && ./scripts/setup.sh --dev"
