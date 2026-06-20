#!/usr/bin/env bash
# scripts/run_req003_real_gateway_tc.sh – 受控运行 TC-003-09（agent 侧 LLM 网关纪律，BUG-030）。
#
# 该用例 automated: false，依赖受控真实厂商凭证 + 隔离测试租户，会产生真实计费 completion，
# 故默认不在 CI/普通 pytest 运行；须由有权操作者显式 opt-in。
#
# 凭证经环境注入（勿写入仓库 / 提交日志 / .env 提交项）：
#   AIFAMILY_REAL_GATEWAY_TC=1   必填，opt-in 闸
#   AIFAMILY_AGENT_EXEC          在 agent-core 容器内执行命令的入口（如 'docker compose -f compose.dev.yaml exec -T agent-core'）
#   AIFAMILY_BASE_URL            agent-core 后端地址（fail-closed 用例必需）
#   AIFAMILY_LITELLM_URL         LiteLLM 网关地址
#   AIFAMILY_LITELLM_MASTER_KEY  LiteLLM master key（用例据此现场创建/清理两个小额度虚拟 key）
#   厂商真实 key 由受控环境注入 LiteLLM，不经本脚本透传
#
# Usage:
#   AIFAMILY_REAL_GATEWAY_TC=1 AIFAMILY_AGENT_EXEC='docker compose -f compose.dev.yaml exec -T agent-core' \
#     AIFAMILY_BASE_URL=... AIFAMILY_LITELLM_URL=... AIFAMILY_LITELLM_MASTER_KEY=... \
#     ./scripts/run_req003_real_gateway_tc.sh
#
# 通过证据：保存脱敏的命令输出、trace_id 与计量断言（见 TC-003-09 手工执行说明）。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(dirname "$SCRIPT_DIR")"; cd "$ROOT"

if [[ "${AIFAMILY_REAL_GATEWAY_TC:-}" != "1" ]]; then
  echo "拒绝运行：须显式 AIFAMILY_REAL_GATEWAY_TC=1（真实凭证 + 计费 completion）" >&2
  exit 2
fi

# 虚拟 key 由用例以 master key 现场创建/清理（确定性小额度），故不再要求预置 VKEY。
required=(AIFAMILY_AGENT_EXEC AIFAMILY_BASE_URL AIFAMILY_LITELLM_URL AIFAMILY_LITELLM_MASTER_KEY)
for v in "${required[@]}"; do
  [[ -n "${!v:-}" ]] || { echo "缺环境变量：$v" >&2; exit 2; }
done

exec uv run --extra dev python -m pytest tests/e2e/test_agent_llm_gateway.py -v
