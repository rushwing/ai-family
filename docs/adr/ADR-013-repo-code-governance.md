---
adr_id: ADR-013
title: "源码仓库与代码治理：模块化单体仓 + 边界仓"
status: accepted
date: 2026-06-14
deciders: [human-001]
informed_by: [codex-007, codex-008, gemini-004/反驳]
supersedes: null
linked_reqs: []
---

## Context（背景与约束）

需要确定五层源码（CLIENT 通道 / AGENT / TOOLSET-MCP / DATA / SECURITY-GOVERNANCE）的仓库组织方式：一个仓还是多个仓、边界划在哪、各仓 CI/CD 与权限怎么配。决策必须吻合以下硬约束：

- **单人开发**（rushwing）：拿不到 polyrepo 唯一真正的红利（团队边界），却要全额付它的税（N+1 仓 / N+1 CI / 依赖版本矩阵 / 跨仓重构）。
- **五层高度耦合**：Agent 共享 LangGraph 基类、MCP 工具调用契约、checkpointer 状态 schema、JWT/OIDC+RLS 鉴权契约；harness（REQ/TC/BUG）与 GLOSSARY 是单一权威，跨层引用频繁。
- **kid 安全红线（硬约束）**：内容/合规策略「在引擎不在 prompt」（04 P6 / 03 §4）。谁能改 kid 安全策略 / RLS / 审计 schema，必须是比"改一个旅行 Agent"更小、更受控的圈子——职责分离是仓库边界的第一性原则。
- **既有资产**：`rushwing/goal-agent`（FastAPI+FastMCP，36 tools，带提交历史）需并入。
- **部署演进**：Phase 1 docker-compose、Phase 2 K3s（GitOps 友好，[ADR-009](ADR-009-compose-to-k3s.md)）。
- **业界参照**：GCP（Architecture Center 仓库最佳实践、Enterprise Foundations Blueprint、Vertex AI Agent Starter Pack 样例为单仓）与 Azure（CAF/WAF、azd 模板为单仓、AI Hub Gateway landing zone）对 SMB AI 的共识 = 模块化单体仓 + 按「安全/生命周期边界」拆极少数仓，**不按 Agent 粒度拆仓**。

## Options（候选项）

### Option A: 纯单体仓（含 infra + governance）
**Pros:** 原子跨层提交最佳；共享契约一次改全见；单人运维成本最低。
**Cons:** IaC（可毁生产的 blast radius）与策略（kid 红线）和业务同权限、同评审，**违背职责分离**；secrets/部署声明与应用代码混在一处。

### Option B: 平台仓 + 每个 Agent 独立仓（用户初始假设）
**Pros:** Agent 天然独立部署/发版；所有权边界清晰（多团队时有价值）。
**Cons:** Agent 并不真正独立——共享基类/工具契约/状态 schema，改一处契约即引发**跨 N 仓版本对齐地狱**；单人付 polyrepo 税无团队红利；原子跨层提交不可能；harness/GLOSSARY 单一权威被打散。**scalable 的真实瓶颈是共享契约变更成本，多仓反而放大它。**

### Option C: 模块化单体仓 + 两个边界仓（选定）
平台单体仓 `ai-family`（应用全层 + `libs/` 共享契约 + harness + docs）内，每个 `agents/<name>/` 是可独立构建/发版的模块（独立 pyproject/Dockerfile/path-filtered CI/版本 tag）；只在两条真实边界上拆出独立仓：`ai-family-infra`（IaC/GitOps，独立 blast radius）与 `ai-family-governance`（安全/合规策略，职责分离）。
**Pros:** 拿到 polyrepo ~90% 的好处（独立构建/发版/所有权），付单仓 ~10% 的成本（契约一致）；契约改动一次 PR 全量可见；吻合 GCP/Azure SMB 共识；红线有 CODEOWNERS 双签兜底；infra 独立隔离生产风险；模块边界即 `git subtree split` 逃生口。
**Cons:** 比纯单体多管 1–2 个仓；需要 path-filtered CI 才能拿到模块级独立构建。

## Decision（决策）

采用 **Option C 的单仓变体（经 2026-06-14 裁决修订，见 Review Notes gemini-004）**：**初期纯 Monorepo `ai-family`**，五层 + `infra/` + `governance/` 均为仓内目录，靠 **path filtering** 做部署/CI 解耦；**不第一天分物理仓**。Agent 模块化但不拆仓。

- **现在**：单仓 `ai-family`，`infra/`（IaC/部署声明）与 `governance/`（受 CODEOWNERS 双签保护）均为目录。
- **后续按触发条件拆物理仓**：当 Agent 规模 / 团队 / 合规审计需要时，再把 `infra/`、`governance/` 或某个 Agent 模块经 `git subtree split` 拆为独立仓（kid 上线 M3 前优先评估 governance）。

详细论证、目录结构、CI/CD 与分支治理见设计稿 [docs/design/07](../design/07-repo-strategy.html)。

## Trade-off（明确放弃了什么）

放弃 Option B 的「Agent 天然独立部署」与「每 Agent 独立仓的所有权清晰」——这些好处在单人 + 强契约耦合下收益低、成本高。换取的是：共享契约的一致性与原子跨层提交、最低的单人运维负担、harness/GLOSSARY 的单一权威。独立部署的诉求改由「模块化 + path-filtered CI + 独立镜像 tag」满足；真正需要把某 Agent 拆出去时（独立团队/开源/独立发布节奏），用 `git subtree split` 沿预留的模块边界切出——届时收益 > 成本。infra 与 governance 物理仓均延后（按触发条件而非固定日期），接受「初期边界靠目录级 CODEOWNERS + path filtering 而非物理隔离」这一过渡态，换取单人迭代不被跨仓 PR 拖慢。

## Consequences（影响）

- **代码结构**：跨层共享物一律进 `libs/` 且只进 `libs/`；Agent 之间禁止横向 import 彼此 `src/`，只依赖 `libs/` 契约——让"同仓"不等于"耦合成一坨"，也让未来 subtree split 依赖清晰可断。
- **CI/CD**：平台仓按变更路径触发构建（改 `agents/goal/**` 只构 goal-agent，改 `libs/**` 触发下游全量回归）；每模块独立镜像 tag 推 NAS 私有 registry；harness TC 作为合并必过门。
- **权限治理**：`.github/CODEOWNERS` 分层，`governance/` 路径强制 human-001 双签；策略以**版本化 bundle 只读下发**给 Agent/Compliance 消费，Agent 仓改动无法绕过或反向篡改策略——把"策略在引擎不在 prompt"保障到源码权限层。
- **infra 目录**：secrets（sops→sealed-secrets）与部署声明在 `infra/` 目录，集群 GitOps 拉取（[ADR-009](ADR-009-compose-to-k3s.md) 混合编排）；CODEOWNERS 对 `infra/` 加严，后续按触发条件可 `subtree split` 为 `ai-family-infra` 独立仓。
- **既有资产**：`rushwing/goal-agent` 经 `git subtree add` 导入 `agents/goal/`（保留历史），随 06 垂直切片改造。
- **里程碑衔接**：M1 起落单仓模块骨架（含 `infra/`、`governance/` 目录）+ path-filtered CI；拆物理仓按触发条件而非固定里程碑（M3 前优先评估 governance）；M5 K3s 化（ADR-009 混合编排）。

## Revisit Trigger（重审触发条件）

- 某 Agent 出现独立团队 / 独立开源 / 与主干显著不同的发布节奏 → 触发该模块 `git subtree split` 为独立仓。
- 平台仓全量 CI 时长超出可接受阈值且 path filter + 缓存已用尽 → 评估按模块拆 CI workflow（仍不拆仓）。
- 合规审计 / 监管要求 governance 必须物理隔离，或 kid 场景临近上线 → 将 `governance/` 升格为 `ai-family-governance` 独立仓（不晚于 M3）。
- `libs/` 膨胀为"上帝包"导致模块隐性耦合 → 按契约细分子包并审查依赖。

## Review Notes（评审追加区）

- [codex-007][2026-06-14] path-filtered CI 写成可实现独立构建但无依赖图来源；libs/** 改动触发“下游全量回归”需知依赖关系 → 已立 REQ-005（依赖图工具 + CI 规则：libs/auth 改动至少触发所有鉴权相关 Agent/MCP/e2e）。human-001 裁决：accept（2026-06-14, REQ-005）
- [codex-008][2026-06-14] 已识别 libs 上帝包但反悔条件只有事后审查，无前置边界 → 已立 REQ-006（libs 分层 contracts/auth/state/agent-sdk 不得反向依赖业务、禁 libs/common、加 import-linter）。human-001 裁决：accept（2026-06-14, REQ-006）
- [gemini-004/反驳][2026-06-14] **与 Codex 对冲**：反对第一天就分 ai-family/ai-family-infra 物理仓——单人跨层改（加一个环境变量）要提两个 PR，拖慢 Draft-First；主张纯 Monorepo + path filtering 部署解耦。Claude：这与本 ADR“infra 因 blast radius 第一天独立”直接冲突，是两份评审的**真实分歧**，留给 human-001 裁决：blast radius 隔离 vs 单人迭代摩擦。human-001 裁决：**采纳 Gemini**——不第一天分仓，先纯 Monorepo + path filtering 做部署解耦；待 Agent 规模到一定程度再考虑拆出 infra/governance 物理仓。正文与 docs/design/07 已据此修订
