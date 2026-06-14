---
adr_id: ADR-004
title: "向量检索底座：Elasticsearch vs pgvector —— pgvector 起步，预留 ES 升级触发线"
status: proposed
date: 2026-06-11
deciders: [human-001]
informed_by: []
supersedes: null
linked_reqs: [REQ-002]
---

## Context（背景与约束）

向量化对象明确：**学习资料**（pdf / html / md / excel），服务 StudyAgent 拍题解答与 KnowledgeAgent 知识库问答。
语料特征：中文为主、规模可控（估算：千份文档 / 数十万 chunk 量级）、按家庭成员隔离、需要"语义相似 + 关键词精确"混合检索
（中文教材里术语精确匹配很重要）。宿主候选：NAS DX4600（Intel N5105 · 16GB 内存，还要跑 PG/Neo4j/Langfuse 等）。
用户点名要求对比 Elasticsearch 与 pgvector。

## Options

### Option A: pgvector（PG 内嵌扩展）（选定为起步方案）

**Pros:**
- **运维一体**：复用 ADR-003 的 PG 实例，备份/监控/迁移零新增；不必再供养一个独立 JVM（NAS 16GB 虽宽松，仍省下一套常驻进程与备份链）
- **隔离同构**：向量表同样吃 RLS，租户隔离与关系数据一个机制、一套 TC，无第二套权限模型
- **混合检索可达**：向量（HNSW，halfvec 降内存）+ PG FTS（zhparser/pg_jieba 中文分词）+ RRF 融合，SQL 内一次完成；还能与业务表 join（"只检索该成员、该学科、近一年的资料"是一个 where 子句）
- 事务一致性：文档元数据、chunk、向量同事务写入，摄取管线无双写一致性问题

**Cons:**
- 全文检索能力弱于 ES（无 BM25 调优生态、中文分词扩展需自编译镜像）
- 单表向量规模到千万级后索引构建/召回性能需要精细调参
- 无开箱即用的检索分析面板

### Option B: Elasticsearch（独立检索引擎）

**Pros:**
- BM25 + dense kNN + RRF 混合检索原生且业界标杆；IK/智能中文分词生态成熟
- 检索调试工具链（explain、analyzer 测试）强，适合"学检索工程"
- 文档级安全（DLS）可模拟租户隔离

**Cons:**
- JVM 常驻 2–4GB——在 NAS 上与 PG/Neo4j/Langfuse 同处会挤占数据层余量（16GB 也并不富裕），且要再起一套备份/快照
- 第二套数据权限模型（DLS 与 PG RLS 并存），双倍隔离测试面
- 摄取双写（PG 元数据 + ES 索引）引入一致性问题；备份/快照另起一套
- license 形态历史波动（可用 OpenSearch 规避，但生态再分叉）

### Option C: 独立向量库（Qdrant/Milvus）
**Pros:** 向量性能与过滤能力强，资源占用小于 ES
**Cons:** 只解决向量不解决全文，混合检索还要拼第三个组件；权限模型仍是第二套。在本场景下两头不占。

## Decision

**v1 用 pgvector + PG FTS（zhparser）做混合检索；ES 不部署，但在本 ADR 写死升级触发线。**

实现要点：
- chunk 表：`(id, family_member_id, doc_id, subject_tags, content, content_tsv, embedding halfvec(1024))`，HNSW 索引 + GIN(tsv) 索引，RLS 启用
- 检索函数：向量 top-k ∪ FTS top-k → RRF 融合 → 可选 rerank（低价 LLM 或 API reranker）
- 嵌入模型经 LiteLLM（ADR-002）调 API；MacMini 上线后可切本地 BGE-M3（嵌入维度与表结构解耦：记录 model+dim 版本列）。**v1 固定 BGE-M3 / 1024 维**——版本列只能识别来源、不能让不同维度共用同一向量列；更换到**不同维度**的 embedding 模型必须走 REQ，采用新向量列或新 `chunk_embedding` 表 + 双写/灰度切换（涉及重嵌入与索引重建；裁决 2026-06-14，见 Review Notes codex-011）

## Trade-off

- 放弃 ES 的 BM25 成熟度与检索调试生态，换取单引擎运维与隔离同构；中文分词质量风险用 zhparser + 评测集验证对冲
- 放弃"顺便学 ES"的机会——检索工程的学习改在 eval 体系（召回率/MRR 评测集）上体现

## Consequences

- PG 镜像需自构建（pgvector + zhparser），Dockerfile 进 infra 仓库；版本升级随 PG 大版本走 REQ
- 摄取管线（docs/design/03）只写 PG 一处；Neo4j 的图写入（ADR-005）是唯二目的地
- 建立检索 golden dataset（≥50 条中文学习资料 QA 对）作为升级触发线的测量基准

## Revisit Trigger（升级 ES/OpenSearch 的条件，满足任一即重审）

1. 检索 golden dataset 上混合检索 top-5 命中率 < 80%，且调参（分词词典/权重/rerank）两轮后仍不达标
2. 活跃 chunk 总量 > 500 万，或 HNSW 重建时间影响每日摄取窗口
3. 出现"检索分析/高亮/聚合"类产品需求（DataAgent 媒体检索升级时可能触发）

## Review Notes

- [codex-011][2026-06-14] 称 BGE-M3 维度非 1024、halfvec(1024) 写死会导致换模型“切不动库”。Claude **驳回事实前提**：BGE-M3 dense 向量确为 **1024 维**，halfvec(1024) 与之一致；且本 ADR §Decision 实现要点已写“记录 model+dim 版本列”。**保留防御性内核**：按 embedding model 版本化列/索引，换模型走 REQ。human-001 裁决：accept 防御性内核（“BGE-M3 非 1024”事实驳回成立）——ADR 正文已补：v1 固定 BGE-M3/1024 维；换到不同维度模型必须走 REQ，采用新向量列或新 chunk_embedding 表 + 双写/灰度切换
