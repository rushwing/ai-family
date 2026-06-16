#!/usr/bin/env bash
# scripts/dev-up.sh – 起本地基座栈（REQ-002）。需 Docker 运行时（OrbStack / colima / Docker Desktop）。
#
# Usage:
#   ./scripts/dev-up.sh            # 起全栈
#   ./scripts/dev-up.sh postgres redis   # 只起指定服务
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

command -v docker >/dev/null || { echo "✗ 需 Docker（建议 OrbStack）"; exit 1; }
docker info >/dev/null 2>&1 || { echo "✗ Docker daemon 未运行（启动 OrbStack/colima）"; exit 1; }

if [[ ! -f infra/.env ]]; then
  cp infra/.env.example infra/.env
  echo "► 已从 infra/.env.example 生成 infra/.env —— 填入密钥后再起需要厂商 key 的服务"
fi

echo "► docker compose up -d $*"
docker compose -f compose.dev.yaml --env-file infra/.env up -d "$@"

echo ""
echo "✓ 起栈中。端口：PG 5432 · Redis 6379 · RabbitMQ 5672/15672 · Keycloak 8081 · LiteLLM 4000 · Langfuse 3001 · MinIO 9000/9001"
echo "  集成测试（起栈后转 passing）："
echo "    AIFAMILY_PG_DSN=postgresql://postgres:\$PG_PASSWORD@localhost:5432/ai_family \\"
echo "    AIFAMILY_REDIS_URL=redis://localhost:6379/0 \\"
echo "    uv run --no-project --with pytest --with 'psycopg[binary]' --with redis pytest tests/integration -v"
echo "  停栈：./scripts/dev-down.sh"
