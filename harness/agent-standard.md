# Agent Standard（多智能体注册与身份映射规范）

本项目用多个 LLM 协助开发与评审。本规范定义**抽象身份 ↔ 实际 LLM** 的注册机制，单一真值在
[`agent-registry.yml`](agent-registry.yml)，校验门 [`tools/check_agents.py`](../tools/check_agents.py)（CI governance-gates 阻塞）。

## 1. 抽象三角色（Planner / Generator / Evaluator）

取自 Anthropic《[Harness Design for Long-Running Agentic Applications](https://www.anthropic.com/engineering/harness-design-long-running-apps)》：

| 角色 | 职责 | 承担状态（handles，= GLOSSARY §9 状态机 owner） |
|---|---|---|
| **Planner** | 把 REQ/目标展开为规格与方案（scope、技术方向、分解），不陷实现细节 | `req_review`（设计侧） |
| **Generator** | 按规格迭代实现（TC 代码/需求代码/文档/迁移），**交付前自检** | `tc_review` / `tc_impl` / `req_impl` |
| **Evaluator** | 独立质量把关：**写 TC 文本定验收标准** + 评审 + 跑门禁判级 | `req_review` / `tc_design` / `tc_impl_review` / `req_impl_review` |
| **human** | 人类编排者：scope 批准、最终合并、blocked 解除、升级裁决（kid 红线/选型） | `draft` / `pr_draft` / `blocked` |

> 🔑 **定标准者 ≠ 实现者**：`tc_design`（写 TC 文本=定验收标准）归 **Evaluator**，`tc_impl`/`req_impl`（写代码）归 **Generator**——同一条产物的"立标"与"实现"分属不同身份，强化分离原则。完整转移表见 [GLOSSARY §9.2](../GLOSSARY.md)。

> 🔴 **分离原则（文章核心）**：Generator 与 Evaluator 必须是**不同身份**——模型对自己的产物有"自夸偏置"，独立 Evaluator 才能给出可迭代的客观反馈。本项目的多 AI 评审（Codex + Gemini）即两个 Evaluator 实例。

为何不用 Orchestrator/Optimizer/Evaluator：上述文章的原生三元组就是 Planner/Generator/Evaluator，且能一一映射到既有 REQ 生命周期；不引入第二套术语。

## 2. 命名与注册

- **命名**：`<role>-NNN`（如 `planner-001`、`evaluator-002`）；人类为 `human-001`。与 rushwing/my-invest-global 同构。
- **一身份多 LLM（候补）**：每个 agent 有 `model`（当前主绑定）+ `fallbacks`（有序候补）。主模型不可用/限流/超额时，编排者顺延到下一候补——**UID 不变**，故评审/提交的归属稳定。
- **一角色多实例**：同一 role 可多个实例并存（如 `evaluator-001`=Codex、`evaluator-002`=Gemini 做对抗评审）。
- **handles**：该 agent 可承担的生命周期状态，取自 requirement-standard §4；校验门确保 handles ⊆ 合法状态集。
- **绑定可演进**：模型能力提升后调整 `model`/`fallbacks` 即可（文章「adaptive architecture」），无需改流程或重写历史。

## 3. 与既有 harness UID 的衔接

Review Notes 历史里的逐条评审 UID（`codex-NNN` / `gemini-NNN`）是 **Evaluator 的产出标识**，归属：`codex-*` → `evaluator-001`，`gemini-*` → `evaluator-002`。历史不重写；新工作按本规范的 role-UID 记录。`claude-code-001`（Claude Code）此前同时承担 Planner+Generator，现拆为 `planner-001` / `generator-001`（物理上仍可为不同模型的 Claude Code 会话）。

## 4. 用法

- 在 REQ/TC/BUG/ADR 中以 role-UID 署名动作（owner / 裁决 / 修复记录）。
- 改 `agent-registry.yml` 走 PR；`tools/check_agents.py` 在 CI 阻塞校验结构与一致性。
- 后续可由 `harness/req-constants.sh` 之类消费者读取 registry 注入流水线（参照 my-invest-global），按需落地。
