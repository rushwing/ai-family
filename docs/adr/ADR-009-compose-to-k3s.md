---
adr_id: ADR-009
title: "部署形态：M1–M4 docker-compose，M5 迁移 K3s（两阶段）"
status: accepted
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

宿主：Pi5（主托管）+ NAS（数据层，绿联系统的 Docker 能力受限于其面板）+ 未来 MacMini。
诉求冲突点：K8S 是显式学习目标，但 GoalAgent 垂直切片要尽快交付建立正反馈。用户已拍板两阶段。

## Options

### Option A: compose 起步 → M5 迁 K3s（选定）
**Pros:** 垂直切片交付最快；K3s 迁移时所有服务已稳定，迁移本身成为干净的学习项目（Helm/Ingress/Secret/探针逐项对照）
**Cons:** 存在"M5 永远不来"的惰性风险——用 REQ + GoalAgent 计划锁住里程碑对冲

### Option B: 直接 K3s
**Pros:** 一步到位，避免迁移返工
**Cons:** 在还没跑通业务时同时调试 K8S 与 Agent 双层问题，定位成本高；Pi5 上 K3s control plane 常驻 ~800MB，挤占 M1 阶段内存

### Option C: 只用 compose
**Pros:** 家庭规模运维最简
**Cons:** 放弃明确的学习目标，不接受

## Decision

**Phase 1（M1–M4）：docker-compose 分栈**——`runtime-stack`（Mac Mini M4：agent-core/网关/IdP/MQ）、`edge-stack`（Pi5：ChatUI/ingress/MCP）与 `nas-stack`（数据层）；618 Mac Mini 到货前，runtime 与 edge 暂并在 Pi5 4GB 上跑开发初期切片。compose 文件即部署文档，进 infra 配置库。
**Phase 2（M5）：混合编排**——**只有 Pi5 跑 K3s**（control-plane + 边缘/部分服务的轻量集群）；**Mac Mini 不进 K3s**，继续以 compose/launchd 跑 agent-core/LiteLLM/Keycloak 等主运行时，作为 K3s 的**外部 runtime 节点**接入；NAS 数据层同样**不进集群**，以 external service 接入。（macOS 无法作 K3s 原生节点、M4 上 Asahi 无成熟支持，故不强行让 Mac 入集群；Pi5 性能不足时升级 16GB。裁决 2026-06-14，见 Review Notes codex-001。）

为降低迁移成本，Phase 1 即遵守的 K8S 友好纪律：
- 全部配置经环境变量/挂载文件注入（12-factor），无容器内状态
- 每服务定义 healthcheck（迁移后变 liveness/readiness 探针）
- 镜像统一私有 registry（NAS 上跑 registry:2），tag 不用 latest
- secrets 不进 compose 文件（.env 文件 + git-crypt / sops，迁移后换 K8S Secret + sealed-secrets）

## Trade-off

- 接受一次有计划的迁移返工（估 2–3 个周末），换取 M1 交付速度与分层调试清晰度
- NAS 数据层永不进 K8S——放弃 StatefulSet 学习样本，用"外部数据服务接入集群"这一更贴近企业现实的模式替代

## Consequences

- M5 迁移检查单（预置）：K3s 安装（disable traefik，换 ingress-nginx 或保留评估）→ Helm chart 化各服务 →
  Ingress + cert（tailnet 内 CA）→ sealed-secrets → HPA 不做（无意义）→ cloudflared 与 Tailscale 以 DaemonSet/host 方式落位 → 演练节点重启自愈
- CI 产物从 M1 起就是镜像，迁移只换编排描述，不动镜像

## Revisit Trigger

- M4 结束后 30 天内未启动 M5（在 GoalAgent 里会触发逾期提醒，需 human-001 显式决定推迟或取消）
- ~~Pi5 资源不足以同时跑 K3s 与全部运行时（届时 MacMini 加入为必选项）~~ → 已落实：Mac Mini M4（16GB）618 加入承载主运行时（compose/launchd），**K3s 阶段作为外部 runtime 节点、不进集群**（混合编排，裁决 2026-06-14）；Pi5 性能不足时升级 16GB

## Review Notes

- [codex-001][2026-06-14] Mac Mini M4 写成 K3s 主 worker 但未定 OS：K3s 不能把 macOS 当原生节点（M4 上 Asahi 亦无成熟支持），M5 第一步即不可执行 → 必须裁决 OS 方案：裸机 Linux / Linux VM / 不进 K3s 仅跑 compose；若 VM 补资源/网络/持久化/重启自愈。Claude：这是 02/ADR-009 写“Mac 为主 worker”时漏掉的硬问题（→ 触发本 ADR 修订）。human-001 裁决：**Mac Mini 不进 K3s**——Pi5 跑 K3s/control-plane（轻量集群），Mac Mini 以 compose/launchd 跑 agent-core/LiteLLM/Keycloak 等主运行时，作为 K3s 的外部 runtime 节点；ADR 改为「混合编排」；Pi5 性能不足时升级 16GB。正文已据此修订
- [codex-006][2026-06-14] M5 检查单漏 external NAS 数据层接缝：DNS/service discovery、tailnet 路由、PG TLS、备份任务、NetworkPolicy、故障切换 → 已立 BUG-004（补 external service runbook + TC）。human-001 裁决：accept（2026-06-14, BUG-004）
- [gemini-反驳][2026-06-14] 强制反驳 + 最可能后悔：单/双节点引入 K3s（Service/Ingress/PVC）纯属无谓抽象，排障认知负载远超收益，违背“单人 = 最大单点”；模块化单体 + compose 才是最优。Claude：与本 ADR“M5 才上 K3s、数据层不进集群”部分对齐，但“是否需要 K3s”本身值得 human 重审。human-001 裁决：同 codex-001——采「混合编排」：K3s 仅在 Pi5/边缘，Mac runtime 与数据层不进集群（不在双节点上堆全套 K8s 抽象）
