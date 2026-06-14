---
adr_id: ADR-001
title: "Agent 编排框架：LangGraph（+ ReAct + PG Checkpointer）"
status: accepted
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-003]
---

## Context（背景与约束）

平台需要统一的编排底座承载 IntentRouter、Planner（Plan Mode 任务图）和 7 个领域 Agent。
核心诉求按优先级：①**长程任务执行韧性**（跨天任务、进程重启续跑、失败重试）；②production 级成熟度与可观测性；
③与既有技能栈（Python/FastAPI）兼容；④学习迁移价值。
约束：算力在云端 LLM，宿主是树莓派5（编排层必须轻量）；goal-agent 已有 FastAPI + FastMCP 资产需要保留。

## Options

### Option A: LangGraph（选定）
**Pros:**
- StateGraph + Checkpointer（官方 PostgreSQL 实现）原生覆盖"断点续跑/重放/人工介入（interrupt）"——与长程韧性诉求直接对位；`interrupt()` 机制天然实现 Plan Mode 的"先批准再执行"
- Python 生态 production 事实标准，与 FastAPI 同进程或独立服务均可；社区/文档/招聘市场迁移价值最高
- 与 Langfuse/LangSmith 深度集成，trace 开箱即用
- 子图（subgraph）机制匹配"Planner 动态组装领域 Agent 任务图"的设计

**Cons:**
- 抽象层有学习成本；API 迭代较快，需锁版本
- 框架魔法可能掩盖底层原理（与"学原理"目标部分冲突）

### Option B: Google ADK
**Pros:** 与 reference.html 的 GCP 企业方案同源（Agent/Session/A2A 抽象），最贴近"学 GCP FDE 思路"；开源可本地跑
**Cons:** 社区规模与第三方集成显著小于 LangGraph；长程持久化与中断恢复能力弱于 LangGraph Checkpointer；与 Gemini 生态耦合倾向

### Option C: 自研 FastAPI + FastMCP + 显式 ReAct（travel_agent 路线）
**Pros:** 完全可控、零框架依赖、学原理最透；goal-agent 已有基础
**Cons:** 任务图、checkpoint、重试、人工介入、并行分支全部自己造轮子——与"production 级组件"原则直接冲突；维护成本随 Agent 数量线性增长

## Decision

选 **LangGraph** 作为全平台编排底座；各 Agent 内部采用 ReAct 范式；状态持久化用 `langgraph-checkpoint-postgres`。

## Trade-off

- 放弃 ADK 的"GCP 同源学习路径"——通过保留 reference.html 映射表（docs/design/00）弥补概念对照
- 放弃自研路线的原理透明度——通过 travel_agent 仓库继续作为教学性 ReAct 参照，平台不复刻
- 接受 LangGraph 版本迭代风险——pyproject 锁定 minor 版本，升级走 REQ 流程

## Consequences

- 每个 Agent = 一个 LangGraph StateGraph + 一个 FastMCP server（工具面），FastAPI 仅作 HTTP/SSE 接入层
- PG 中新增 langgraph checkpoint schema（与业务 schema 分离，同样受备份链路覆盖）
- goal-agent 的 APScheduler 定时逻辑改造为"定时触发图入口"（REQ-003）
- Planner 的任务图 = 动态构建的父图，领域 Agent 以子图/工具节点形式挂载

## Revisit Trigger

- LangGraph 出现破坏性 license/收费变更
- Checkpointer 在 Pi5 + NAS PG 环境下 p95 状态写入 > 500ms 且无法优化
- 单图节点数 > 50 导致可维护性问题（届时评估拆分或换编排形态）

## Review Notes

- [codex-002][2026-06-14] checkpoint ≠ 精确一次恢复：未定义幂等键/副作用去重，kill-retry 可能重复执行工具或重复发提醒 → 已立 BUG-001（idempotency_key + outbox + 去重 TC）。human-001 裁决：accept（2026-06-14）
- [gemini-001][2026-06-14] agent-core(Mac) 与 PG checkpointer(NAS) 跨设备，ReAct 每步高频读写恐拖慢回复，建议 checkpointer 移 Mac 本地。Claude 校准：本 ADR Revisit Trigger 已含“p95 写入 > 500ms”，Gemini 称的“数秒”量级或高估（千兆 LAN 单写 ~1-5ms），建议 M1 实测后定 checkpointer 落点。human-001 裁决：pending——M1 实测延迟后再决定是否纳入（checkpointer 落点）
- [gemini-反驳][2026-06-14] 强制反驳：LangGraph 过底层、需手写大量状态流转，Draft-First 快速验证不如高层框架（Dify/Coze）快 10×。Claude：与 P1“production 级”取舍冲突，reference.html 同源学习目标支撑原选择，记录待裁。human-001 裁决：reject——已有 LangGraph 项目经验、学习成本不高；Dify/Coze 可扩展性明显偏低、不符要求，保留 LangGraph
