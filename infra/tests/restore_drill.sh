#!/usr/bin/env bash
# TC-002-10：备份链路 + PITR 恢复演练（含 MinIO/Neo4j，BUG-010）。infra 未就绪 skip。
set -euo pipefail
if [[ -z "${AIFAMILY_BACKUP_TARGET:-}" ]]; then
  echo "SKIP TC-002-10：未设 AIFAMILY_BACKUP_TARGET（备份链路未就绪）"; exit 0
fi
# TODO(req_impl): PG 基础备份+WAL 异地 / PITR 恢复一次 / MinIO+Neo4j 在备份范围 / 记 RTO·RPO
echo "TODO: 实现备份+恢复演练"; exit 1
