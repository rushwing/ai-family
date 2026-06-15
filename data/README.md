# data/ —— DATA 层

- `migrations/` —— PostgreSQL（RLS · pgvector · zhparser）Alembic 迁移；**RLS 加固随迁移一次性内建**
  （FORCE RLS / 受限迁移 role / 默认禁 SECURITY DEFINER / 平台状态表同纳入，BUG-002 / BUG-014）
- `neo4j/` —— 本体 cypher / 约束（KnowledgeAgent，M3）
- `ingest/` —— ingest-worker（解析 / 嵌入 / 图谱抽取，M3）

> M1：`migrations/` 随 REQ-003 数据迁移（MariaDB→PG16）落地。`neo4j/`、`ingest/` 为后续里程碑占位。
