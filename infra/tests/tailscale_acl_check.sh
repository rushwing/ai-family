#!/usr/bin/env bash
# TC-002-01：Tailscale 四节点互通 + ACL 生效（在 tailnet 内的 runner 执行）。
# infra 未就绪时 skip（exit 0）。req_impl 起 tailnet + 应用 infra/tailscale/acl.json 后启用。
set -euo pipefail
if [[ -z "${AIFAMILY_TAILNET:-}" ]]; then
  echo "SKIP TC-002-01：未设 AIFAMILY_TAILNET（tailnet 未就绪）"; exit 0
fi
command -v tailscale >/dev/null || { echo "✗ 需 tailscale CLI"; exit 1; }
# TODO(req_impl): tailscale ping 四节点；ingress→runtime:8000 通 / ingress→NAS:5432 拒；kid 默认拒；admin SSH check
echo "TODO: 实现 ACL 探测（对齐 docs/design/02 §3 / infra/tailscale/acl.json）"; exit 1
