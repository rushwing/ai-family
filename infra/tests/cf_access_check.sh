#!/usr/bin/env bash
# TC-002-02：Cloudflare Tunnel + Access（外网 runner）。infra 未就绪 skip。
set -euo pipefail
if [[ -z "${AIFAMILY_PUBLIC_DOMAIN:-}" ]]; then
  echo "SKIP TC-002-02：未设 AIFAMILY_PUBLIC_DOMAIN（CF Tunnel 未就绪）"; exit 0
fi
# TODO(req_impl): 未登录被 Access 拦截 / 白名单登录可达 / nmap 确认零入站端口 / 非白名单拒
echo "TODO: 实现 CF Access 探测（infra/cloudflare/ + docs/design/02）"; exit 1
