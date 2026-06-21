-- 0003_graph_runtime —— REQ-003 WP-3：agent-core 长程图运行时表 + 精确一次语义（BUG-001/013）。
-- 承 0001/0002 的 RLS 约定（member 隔离 + ENABLE/FORCE）。幂等可重复执行。
--
-- 精确一次（exactly-once）机制：
--   * 副作用节点在**同一事务**写「业务行(graph_business) + outbox 意图 + 计分」，
--     均带 idempotency_key，UNIQUE(family_member_id, idempotency_key) + ON CONFLICT DO NOTHING 去重；
--   * checkpoint（lg_checkpoint，0002）仅记控制流，与业务事务分离；
--   * 投递 relay 读 outbox 投递，落 graph_delivery（同 UNIQUE）→ 至多一次外部投递；
--   * 崩溃恢复以**已提交业务状态**为权威 reconcile（idempotency_key 已在即视为完成，不重复）。

CREATE TABLE IF NOT EXISTS graph_business (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  idempotency_key text NOT NULL,
  node text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (family_member_id, idempotency_key)
);
ALTER TABLE graph_business ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_business FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON graph_business;
CREATE POLICY member_isolation ON graph_business
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON graph_business TO aifam_app;

CREATE TABLE IF NOT EXISTS graph_score (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  idempotency_key text NOT NULL,
  points int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (family_member_id, idempotency_key)
);
ALTER TABLE graph_score ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_score FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON graph_score;
CREATE POLICY member_isolation ON graph_score
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON graph_score TO aifam_app;

CREATE TABLE IF NOT EXISTS graph_delivery (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  idempotency_key text NOT NULL,
  channel text NOT NULL DEFAULT 'notify',
  delivered_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (family_member_id, idempotency_key)
);
ALTER TABLE graph_delivery ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_delivery FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON graph_delivery;
CREATE POLICY member_isolation ON graph_delivery
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON graph_delivery TO aifam_app;

-- outbox 幂等唯一约束（0002 建表，未加唯一）：同一 (member, idempotency_key) 仅一条意图
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT FROM pg_constraint WHERE conname = 'outbox_member_idem_uniq'
  ) THEN
    ALTER TABLE outbox ADD CONSTRAINT outbox_member_idem_uniq
      UNIQUE (family_member_id, idempotency_key);
  END IF;
END $$;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aifam_app;
