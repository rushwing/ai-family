---
adr_id: ADR-002
title: "LLM 接入：LiteLLM 统一网关 + 按场景模型路由"
status: proposed
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

可用模型资源分两类：**订阅类**（Claude Code Pro、Codex Plus、Gemini 家庭版——服务于开发态，不可程序化用于运行时）
与**按量 API**（DeepSeek V4、Kimi/Moonshot、Claude API、Gemini API——运行时主力）。
平台需要：统一接入点、按家庭成员配额、按任务复杂度路由模型（reference.html 的 Flash/Pro 分层思想）、成本可观测。

## Options

### Option A: LiteLLM Proxy（选定，proposed）
**Pros:**
- OpenAI 兼容统一入口，100+ 后端；Agent 代码与具体厂商解耦（goal-agent 已用 OpenAI SDK，零改造接入）
- 内置 virtual key / per-key 预算与限流——直接映射"每个家庭成员一个 key"的配额需求
- 自带失败转移（fallback chain：DeepSeek → Kimi → Claude）、prompt cache 透传、成本统计回调（对接 Langfuse）
- production 部署形态成熟（docker 单容器 + PG 配置库）

**Cons:** 多一跳代理延迟（局域网内 ~ms 级，可接受）；配置面较杂，需收敛使用面

### Option B: 各 Agent 直连厂商 SDK
**Pros:** 少一个组件、零代理延迟
**Cons:** 配额/路由/审计逻辑散落各 Agent；换模型要改代码；成本统计要自建——违背 production 原则

### Option C: OneAPI/new-api 类网关
**Pros:** 中文生态、计费面板友好
**Cons:** 治理能力（预算、fallback、可观测集成）弱于 LiteLLM；社区分叉多、维护可持续性存疑

## Decision

部署 **LiteLLM Proxy** 于 Pi5，作为平台唯一 LLM 出口。模型路由策略（v1）：

| 场景 | 模型档位 | 候选 |
|---|---|---|
| 意图分类 / 简单摘要 / Compliance LLM-judge | 低价快档 | DeepSeek-chat、Kimi 低档 |
| 领域 Agent ReAct 主循环 | 中档 | DeepSeek V4、Kimi k2.5 |
| Planner 复杂分解 / StudyAgent 深度讲解 / StockAgent 推理 | 高档 | Claude（按量）、DeepSeek-reasoner |
| Embedding | 嵌入档 | 经网关接 API 嵌入模型（预留 MacMini 本地 BGE-M3 选项，见 ADR-004） |

订阅类资源**不进入运行时链路**，仅用于开发态（分工见 docs/design/05 的 token 策略）。

## Trade-off

- 接受一跳代理与一个新组件的运维成本，换取模型可替换性、家庭成员级配额和统一成本观测
- 路由档位是人工静态配置，放弃"自动复杂度路由"的精巧性（v1 由 IntentRouter 的风险分级粗选档位即可）

## Consequences

- 所有 Agent 的 base_url 指向 LiteLLM；厂商 API key 只存在于网关的 secret 中，Agent 侧无任何厂商凭证
- 家庭成员 virtual key 由 IdP 注册流程同步创建；超配额行为返回明确错误并在 ChatUI 呈现
- Langfuse 成本面板以 LiteLLM 回调为数据源

## Revisit Trigger

- 网关单点故障影响可用性 ≥ 2 次/月（届时评估双实例或 sidecar 直连降级）
- 运行时月度 token 成本连续 2 个月超预算 50%（重审路由档位与缓存策略）

## Review Notes

- [codex-004][2026-06-14] 网关作预算硬顶/key 唯一持有者但无强制机制：key 同步失败、计数延迟、网关宕机降级、Agent 直连禁令均无验证 → 已立 BUG-003（CI secret 扫描 + egress 限制 + fail-closed 定义 + 预算超限打真实网关 TC）。human-001 裁决：accept（2026-06-14, BUG-003）
- [gemini-gap][2026-06-14] 【最大缺口】无成本熔断 / ReAct 死循环阻断：工具连环失败重试可一夜刷爆 API（比宕机更致命）。本 ADR 是天然落点 → 已立 REQ-007（token/金额硬熔断 + 循环步数上限），建议配套立 ADR-014。human-001 裁决：accept（2026-06-14）——支持 REQ-007，批准新立 ADR-014（成本熔断）
