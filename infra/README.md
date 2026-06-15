# infra/ —— 基础设施即代码 / 部署声明（目录起步）

部署声明与 secrets（sops+age →（M5 K3s）sealed-secrets）；集群 GitOps 拉取
（ADR-009 混合编排：仅 Pi5 入 K3s，Mac Mini/NAS 外部接入）。

- **blast radius 独立**：受 CODEOWNERS 加严；secrets 永不进应用代码路径。
- **不第一天分物理仓**（2026-06-14 裁决，ADR-013）：先目录 + path filtering；
  按触发条件再 `git subtree split` 为 `ai-family-infra`。

> M1：本地起栈见根 `compose.dev.yaml`；生产部署声明随 REQ-002 基座落地。占位骨架。
