---
adr_id: ADR-006
title: "异步消息总线：RabbitMQ（Kafka 落选）"
status: proposed
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

需要异步化的工作负载：摄取管线（解析/嵌入耗时分钟级）、定时报表生成、通知分发（Telegram/邮件）、
图谱抽取、备份任务事件。特征：低吞吐（< 1 msg/s 均值）、任务型（需要 ack/重试/死信）、消费者是 Python worker。
**注意边界：Agent 编排状态不走消息总线**（LangGraph + PG checkpointer 负责，见 ADR-001）；总线只承载"任务分发"语义。
用户技能栈同时熟悉 RabbitMQ 与 Kafka。

## Options

### Option A: RabbitMQ（选定）
**Pros:** 任务队列语义原生（ack、重试、TTL、死信、优先级）；单容器 ~150MB 内存跑在 Pi5 无压力；管理台直观；Python aio-pika 成熟
**Cons:** 不是事件溯源/流处理形态，未来要做"事件回放"需另想办法（家庭场景基本不会）

### Option B: Kafka（含 Redpanda 等兼容实现）
**Pros:** 事件流/回放/多消费组范式，企业大数据学习价值
**Cons:** 任务队列语义要自己拼（无原生 per-message ack 重试/死信）；JVM Kafka 在 Pi5 不现实，Redpanda 也偏重；对 <1 msg/s 的负载是教科书式 over-design——连"小微企业适中"的标尺都超了

### Option C: PG 表实现队列（SKIP LOCKED）/ Redis Streams
**Pros:** 零新组件
**Cons:** 死信/重试/监控都要手搓；放弃用户已熟悉的 MQ 资产；Redis Streams 持久性弱

## Decision

**RabbitMQ 3.13+，部署于 Pi5**，quorum queue + 死信交换机。
拓扑 v1：`ingest.docs`（摄取）、`graph.extract`（图谱抽取）、`notify.out`（通知）、`report.gen`（报表）、各配 DLQ。
消息体统一带 `family_member_id` 与 `trace_id`（贯通 Langfuse 链路）。

## Trade-off

- 放弃 Kafka 的流处理学习机会——该学习目标已由本项目其他企业组件（RLS/OIDC/K3s/可观测）覆盖，不强行塞入
- 接受"未来若要事件回放需补审计表"的限制（审计表本就在 PG，见 ADR-012）

## Consequences

- 摄取管线 worker（Python, aio-pika）独立容器部署，可水平加副本
- 通知统一经 `notify.out` 出口（Telegram/邮件 worker 消费），Agent 不直连通知渠道

## Revisit Trigger

- 出现真实的流式场景（如行情 tick 流给 StockAgent）——届时单独为该场景评估 Redpanda，而非整体迁移
- 消息峰值 > 100 msg/s 持续出现

## Review Notes

- [gemini-003][2026-06-14] 过度工程质疑：家庭规模可用 PG LISTEN/NOTIFY + SKIP LOCKED 替代 RabbitMQ/Redis，省一组常驻进程。Claude 校准：RabbitMQ 在 Mac(16GB)、PG 在 NAS(16GB)，非同机，OOM 前提弱于原述；但“家庭规模是否需要独立 MQ”的质疑成立，值得 M1 前重审本 ADR。human-001 裁决：待定
