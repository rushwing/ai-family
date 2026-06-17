#!/usr/bin/env bash
# TC-002-07：RabbitMQ 管理台仅 tailnet 内可达。infra 未就绪 skip。
set -euo pipefail
if [[ -z "${AIFAMILY_RABBITMQ_MGMT:-}" ]]; then
  echo "SKIP TC-002-07：未设 AIFAMILY_RABBITMQ_MGMT（RabbitMQ 未就绪）"; exit 0
fi
# TODO(req_impl): tailnet 内 :15672 可登录 + 收发 notify.out；公网/非 tailnet 不可达
echo "TODO: 实现 RabbitMQ 探测"; exit 1
