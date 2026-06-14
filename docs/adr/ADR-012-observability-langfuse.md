---
adr_id: ADR-012
title: "可观测与审计：Langfuse（LLM 层）+ Prometheus/Grafana/Loki（基础设施层）+ PG 审计表"
status: proposed
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

用户拍板 LangSmith/Langfuse 方向。三类观测需求：
①**LLM 行为**：每次请求的执行树（图节点、LLM 调用、工具调用、token、成本、延迟）、prompt 版本、eval 数据集；
②**基础设施**：Pi5/NAS 资源水位、容器健康、队列深度；
③**审计**（治理需求，区别于观测）：不可变更的"谁让 AI 做了什么"记录，含 Compliance 拦截事件。

## Options

### Option A: Langfuse self-host（选定为 LLM 层）
**Pros:** 开源可自托管（数据不出家门，符合本地化原则）；LangGraph/LiteLLM 双向集成；trace/成本/prompt 管理/datasets+eval 全覆盖；OSS 版功能足够
**Cons:** v3 架构引入 ClickHouse 依赖（NAS 上 ~1GB 内存），部署件数增加

### Option B: LangSmith（SaaS）
**Pros:** 与 LangGraph 同厂、体验最顺滑、零运维
**Cons:** 全家对话数据上 SaaS——与"重要数据本地托管"原则冲突（儿童对话尤其敏感）；免费档限额

### Option C: 纯 OTel + Grafana Tempo 自拼 LLM 观测
**Pros:** 单一观测体系
**Cons:** token/成本/prompt/eval 语义全要自建，重复造 Langfuse

## Decision

- **LLM 层：Langfuse v3 self-host 于 NAS**（含 ClickHouse），LangGraph callback + LiteLLM 回调双路上报，trace_id 全链路贯通（ChatUI 生成，HTTP header → LangGraph → MCP 网关 → RabbitMQ 消息体）
- **基础设施层：Prometheus + Grafana + Loki**（node-exporter / cadvisor / postgres-exporter / rabbitmq-exporter），Grafana OIDC 接 IdP，仅 tailnet 可达
- **审计层：PG `audit` schema 独立表**（append-only，应用账号仅 INSERT 权限）：`(trace_id, member_id, role, event_type[prompt|tool_call|retrieval|output|compliance_block|confirm_action], payload_digest, created_at)`。
  Langfuse 是分析视图，审计表是权威记录——两者职责分离，Langfuse 数据可清理，审计表不可
- 开发态可并行开 LangSmith 试用作对照学习，但**运行时数据只进 Langfuse**

## Trade-off

- 接受 Langfuse v3 + ClickHouse 的部署重量，换取数据不出家门与完整 LLM 工程功能（eval datasets 直接服务 harness 的 eval 级 TC）
- 三套系统（Langfuse/Grafana 栈/审计表）有学习与维护成本——以"企业观测与治理本就分层"作为学习正当性

## Consequences

- M1 验收含"一次请求在 Langfuse 看到完整 trace"（REQ-002）
- 每月成本报表（per-member token 花费）从 Langfuse API 出，由 GoalAgent 周报引用
- 告警 v1 仅三条：节点磁盘 >85%、备份任务失败、DLQ 非空（Grafana → notify.out → Telegram）

## Revisit Trigger

- NAS 内存无法同时容纳 PG/Neo4j/MinIO/Langfuse 栈（优先评估 Langfuse 迁 MacMini）
- Langfuse OSS 功能阉割或 license 变化

## Review Notes

（待评审追加）
