#!/usr/bin/env bash
# scripts/test.sh – 分发模块测试（modular monorepo：各模块自带测试与 venv）。
#
# Usage:
#   ./scripts/test.sh            # 列出可测模块
#   ./scripts/test.sh goal [...] # 跑 agents/goal 测试（透传额外参数给其 test.sh）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

MODULE="${1:-}"
shift || true

if [[ -z "$MODULE" ]]; then
  echo "可测模块："
  for m in agents/*/scripts/test.sh; do
    [[ -f "$m" ]] && echo "  - $(echo "$m" | cut -d/ -f2)"
  done
  echo "用法：./scripts/test.sh <module> [pytest args]"
  exit 0
fi

TARGET="agents/$MODULE/scripts/test.sh"
if [[ -f "$TARGET" ]]; then
  echo "► 运行 $TARGET $*"
  exec "$TARGET" "$@"
fi

echo "✗ 模块 '$MODULE' 暂无 scripts/test.sh。"
echo "  （切片改造接入平台 TC 后，模块测试随 REQ-005 纳入 CI 阻塞门。）"
exit 1
