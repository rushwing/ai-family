---
adr_id: ADR-005
title: "知识图谱：Neo4j Community 承载家庭本体（Ontology 初步应用）"
status: accepted
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: []
---

## Context（背景与约束）

用户明确要求引入图数据库 Neo4j 做实体对象关联（Ontology 初步应用）。
业务动机：KnowledgeAgent 需要跨域的实体关联视图——成员、目标、学习主题、知识点、地点、行程、投资标的之间的关系，
为其他 Agent 提供"中间状态 context"（如 StudyAgent 问"小孩最近薄弱知识点"→ 图谱一跳查询；TravelAgent 关联"去过的城市/想去清单"）。
这类多跳关系查询在关系库里是递归 join，在图谱里是天然形态。

## Options

### Option A: Neo4j Community（选定）
**Pros:** 图数据库事实标准，Cypher 学习价值高；LangChain/LlamaIndex GraphRAG 集成最成熟；浏览器可视化对"家庭知识地图"产品形态有直接价值
**Cons:** Community 版无内置多租户（多 database 是企业版功能）与细粒度权限；JVM 常驻 ~1GB；备份只能离线 dump

### Option B: PG + Apache AGE（图扩展）
**Pros:** 复用 PG 实例与 RLS，零新组件
**Cons:** 生态小众、Cypher 子集不全、与 pgvector/zhparser 同镜像共存增加构建复杂度；学习迁移价值低

### Option C: 不引入图谱，关系建模在 PG
**Pros:** 最省运维
**Cons:** 多跳查询与本体演进笨重；放弃 GraphRAG 学习目标——与用户显式要求冲突

## Decision

**Neo4j Community 5.x，部署于 NAS**，由 KnowledgeAgent 独占写入口（其他 Agent 只读，经 KnowledgeAgent 的 MCP tools 访问）。

本体 v1（受控起步，宁缺勿滥）：

```
节点: Member, Goal, Topic(学习主题), KnowledgePoint, Place, Trip, Ticker(标的), Document
关系: OWNS(Member→Goal), STUDIES(Member→Topic), CONTAINS(Topic→KnowledgePoint),
      WEAK_AT/MASTERED(Member→KnowledgePoint, 带时间与置信度), VISITED/WISHES(Member→Place),
      PART_OF(Place→Trip), WATCHES/HOLDS(Member→Ticker), EVIDENCED_BY(任意→Document, 指向 pgvector chunk)
```

租户隔离方案（Community 无多库的补偿设计）：
- 所有节点带 `member_id` 属性；私有子图查询一律经 KnowledgeAgent MCP tools，工具侧按 JWT 注入 `WHERE n.member_id = $sub` —— **应用层隔离，强度低于 PG RLS，已知妥协**
- 家庭共享实体（Place、Topic 公共部分）以 `member_id = 'family'` 标记

## Trade-off

- 接受第二个数据引擎的运维成本与应用层隔离的较弱保证（图谱中不存放高敏数据：成绩细节、持仓数量等仍在 PG，图谱只存关系骨架——以**数据极小化**对冲权限模型缺口）
- 放弃 AGE 的单引擎简洁性，换取 Cypher/GraphRAG 生态与可视化能力

## Consequences

- 摄取管线双目的地：chunk→pgvector，实体/关系抽取（LLM 结构化输出）→Neo4j，经 RabbitMQ 异步、允许图谱滞后
- `EVIDENCED_BY` 关系持有 pgvector chunk id，实现"图谱定位 + 向量取证"的 GraphRAG-lite 检索
- 本体治理：本 ADR 只管**本体治理原则**（命名/隔离/数据极小化）；具体本体 schema（节点/关系定义）放版本化目录 `data/neo4j/ontology`，新增/变更走 REQ/TC，不再每次改 ADR 附录（避免决策记录与 schema migration 混淆、卡住 KnowledgeAgent 迭代；裁决 2026-06-14，见 Review Notes codex-012）

## Revisit Trigger

- 图谱中不可避免要存敏感属性（届时评估 Neo4j 企业版或回迁 PG+AGE）
- NAS 内存压力导致 Neo4j 与 PG 互相影响（评估迁至 MacMini）

## Review Notes

- [codex-012][2026-06-14] “本体变更走 ADR 附录”过重，每加关系改 ADR 会把决策记录与 schema migration 混淆，KnowledgeAgent 迭代会卡文档流程 → 建议 ADR 只管本体治理原则，具体 schema 放版本化 data/neo4j/ontology，变更走 REQ/TC（→ 触发本 ADR 修订）。human-001 裁决：accept——ADR 只管本体治理原则，具体 schema 移版本化 data/neo4j/ontology 走 REQ/TC；正文已据此修订
- [gemini-反驳][2026-06-14] 强制反驳：家庭图谱 < 十万节点，PG+AGE 或递归 CTE 即可；Neo4j 吃内存且带 PG↔Neo4j 跨库一致性噩梦。Claude：与 G3 过度工程线呼应；本 ADR 已用“数据极小化 + 异步允许滞后”对冲一致性，记录待裁。human-001 裁决：accept Claude 意见——保留 Neo4j；以「数据极小化 + 异步允许滞后」对冲一致性，图谱不存高敏属性（成绩/持仓在 PG）
