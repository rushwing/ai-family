---
adr_id: ADR-003
title: "数据底座与租户隔离：PostgreSQL 16 + RLS（租户 = 家庭成员）"
status: accepted
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002, REQ-003]
---

## Context（背景与约束）

家庭多成员（含未成年人）共用一套平台，要求账号级数据隔离：目标/打卡、学习资料、旅行计划、持仓数据互不可见
（除非显式共享）。用户已拍板关系底座用 PostgreSQL；goal-agent 现用 MariaDB 需迁移。
规模：≤10 用户、单实例、无高并发——隔离的目的是**安全与学习企业租户模式**，不是横向扩展。

## Options

### Option A: 单库单 schema + RLS 行级隔离（选定）
**Pros:**
- 企业 SaaS 最主流的 pooled 租户模型，学习价值最高；reference.html 的 "row-level security policy binding" 同款思路
- 防御纵深的最后一层：即使应用层鉴权有 bug，DB 仍按 `app.current_member` 会话变量裁剪行
- 备份/迁移/运维一份；pgvector 向量数据同享 RLS（与 ADR-004 协同）

**Cons:** RLS 策略写错会静默漏数据，必须有专门 TC（跨成员读取返回 0 行）；连接池需正确传递会话变量（asyncpg + `SET LOCAL`）

### Option B: schema-per-member
**Pros:** 隔离边界更硬，误查跨界直接报错
**Cons:** Alembic 迁移 ×N、跨成员共享数据（家庭共享日历/知识）反而要打洞；10 人规模收益小于成本

### Option C: database-per-member
**Pros:** 最强隔离
**Cons:** 家庭场景纯属过度设计；连接数与备份成本 ×N

## Decision

**PostgreSQL 16，单库，业务表统一带 `family_member_id UUID NOT NULL`，启用 RLS。**

关键设计：
- 应用以非超级用户连接；每事务 `SET LOCAL app.current_member = '<jwt.sub>'`；策略：`USING (family_member_id = current_setting('app.current_member')::uuid)`
- 共享数据（家庭共同知识、共享行程）单独建表，用 `shared_with` 数组列 + 独立 RLS 策略，**不**给私有表开例外
- `admin` 角色经独立 DB role 走 `BYPASSRLS` 仅用于运维脚本，应用路径永不使用
- LangGraph checkpoint schema 与业务 schema 分离，checkpoint 表同样带成员维度
- goal-agent 迁移：SQLAlchemy 方言切换（aiomysql → asyncpg）、Alembic 基线重建、数据搬迁脚本（REQ-003）

## Trade-off

- 接受 RLS 配置错误风险（用强制 TC + code review 清单对冲），换取单实例运维 + 企业级租户模式的学习样本
- 放弃 schema 级硬边界——家庭信任模型下行级隔离足够，且共享场景更自然

## Consequences

- 所有新表的 DDL 模板必须含 family_member_id + RLS 策略（进 harness 的实现检查清单）
- 工具侧鉴权（ADR-010）与 RLS 形成双层防御：JWT 校验在前，行裁剪兜底
- PG 部署于 NAS（SSD 缓存卷），备份链路见 ADR-011

## Revisit Trigger

- 出现需要 per-tenant 加密密钥的合规场景
- 单库体积 > 200GB 或慢查询无法用索引解决（评估拆库）

## Review Notes

- [codex-003][2026-06-14] RLS 仅覆盖正常应用查询，未覆盖 SECURITY DEFINER 函数 / 迁移脚本 / 后台 worker / 连接池复用 / admin 脚本绕过路径（生产事故常见入口）→ 已立 BUG-002（FORCE RLS + 迁移受限 role + worker 必设 member/shared scope + 默认禁 SECURITY DEFINER + CI 扫描新表 RLS）。human-001 裁决：accept（2026-06-14, BUG-002）
