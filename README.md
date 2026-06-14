# ai-family — 家庭 AI Agent 集群（Family Agent Platform）

> 一套面向家庭多成员的 production 级多智能体平台。参考 GCP 企业 AI Agent 解决方案的架构方法论（见 `reference.html`），
> 以 **GoalAgent 垂直切片** 为起点，以点到面，边做应用边夯实基座。
> 同时这是一个学习项目：目标是完整走一遍企业级 AI 落地的设计→评审→灰度→放量流程。

**当前阶段：M0 — 架构设计稿 v1（待 Codex / Gemini 架构评审）**

## 渐进式披露导航（按需深入，不要一次读完）

| 层级 | 读什么 | 回答什么问题 |
|---|---|---|
| **L0** | 本 README | 这是什么项目，现在处于什么阶段 |
| **L1** | [docs/design/00-overview.html](docs/design/00-overview.html) | 全景架构、设计原则、文档地图 |
| **L2** | [01 架构与组件](docs/design/01-architecture.html) · [02 部署与网络安全](docs/design/02-deployment-network.html) · [03 数据流与租户隔离](docs/design/03-dataflow-tenancy.html) · [04 选型决策矩阵](docs/design/04-tech-selection.html) · [05 Rollout 与 ROI](docs/design/05-rollout-roi.html) · [06 GoalAgent 垂直切片](docs/design/06-goalagent-vertical.html) | 每个领域的具体设计 |
| **L3** | [docs/adr/](docs/adr/)（12 个决策记录） · [harness/tasks/](harness/tasks/)（REQ/TC/BUG） | 为什么这么选、当前在做什么 |

## 一图速览

- **形态**：ChatUI（NextJS）→ IntentRouter → Planner → 七个领域 Agent（Goal/Study/Travel/Stock/Research/Knowledge/Data）→ MCP 工具层 → 数据底座，全程被 Compliance 双向审查与 Langfuse 全链路追踪覆盖。
- **编排**：LangGraph + ReAct，PostgreSQL checkpointer 提供长程任务韧性（断点续跑）。
- **底座**：PostgreSQL 16（RLS 租户隔离 + pgvector）· Neo4j（家庭知识图谱）· RabbitMQ · Redis · MinIO/NAS。
- **硬件**：树莓派5 4GB（轻量接入节点）+ 绿联 NAS DX4600（N5105 · 16GB · 数据层）+ Mac Mini M4 16GB（618 入手 · 主运行时 + OpenClaw 宿主）+ 小额 VPS（异地备份）。
- **网络**：Tailscale mesh（零公网端口）+ Cloudflare Tunnel/Access（唯一对外入口）。

## 工程方法（harness engineering）

需求、测试用例、缺陷、架构决策全部文件化管理，约定见 [harness/README.md](harness/README.md)：

- 需求 `harness/tasks/features/REQ-NNN.md` · 测试用例 `TC-NNN-SS.md` · 缺陷 `BUG-NNN.md`
- 架构决策 `docs/adr/ADR-NNN-*.md`（含落选项 pros/cons 与重审触发条件）
- 术语以 [GLOSSARY.md](GLOSSARY.md) 为唯一权威，所有文档引用其中定义，防止术语漂移

## 项目纪律（防 scope 外溢）

1. 前端设计稿（Claude Design 产出）= 产品 scope 边界，设计稿之外的功能不进开发队列
2. 只有 GoalAgent 做到详设深度，其余 Agent 保持 L1 框图深度，做到哪层细化到哪层
3. 本项目的开发计划本身录入 GoalAgent 管理（dogfooding）
4. 设计变更必须先改 ADR / 设计稿，再改代码
