#!/usr/bin/env bash
# scripts/dev-down.sh – 停本地基座栈。--volumes 连数据卷一起删。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(dirname "$SCRIPT_DIR")"; cd "$ROOT"
docker compose -f compose.dev.yaml down "$@"
