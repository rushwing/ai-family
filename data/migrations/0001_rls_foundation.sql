-- 0001_rls_foundation —— REQ-002 数据面 RLS 基座（BUG-002 / BUG-011 / BUG-015）
-- 幂等：可重复执行（IF EXISTS / IF NOT EXISTS）。生产由迁移工具按序应用；CI/测试直接执行。
--
-- 约定：
--   * 应用以非超级、无 BYPASSRLS 的角色 aifam_app 访问（经 SET ROLE / 连接角色）。
--   * 每事务注入成员身份：SELECT set_config('app.member_id', '<uid>', true)（per-txn，禁 session 级）。
--   * 所有 tenant-bearing 表 ENABLE + FORCE ROW LEVEL SECURITY + member 隔离策略。

-- 1. 应用角色（无 SUPERUSER / 无 BYPASSRLS）
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aifam_app') THEN
    CREATE ROLE aifam_app NOLOGIN;
  END IF;
END $$;

-- 2. 当前成员（缺省空 → 默认拒绝）
CREATE OR REPLACE FUNCTION app_current_member() RETURNS text
  LANGUAGE sql STABLE AS $$ SELECT current_setting('app.member_id', true) $$;

-- 3. 业务表示例：member_note（每个 tenant-bearing 业务表同此模式）
CREATE TABLE IF NOT EXISTS member_note (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  family_member_id text NOT NULL,
  body text,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE member_note ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_note FORCE ROW LEVEL SECURITY;        -- 表 owner 也受约束
DROP POLICY IF EXISTS member_isolation ON member_note;
CREATE POLICY member_isolation ON member_note
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());   -- 防越权写他人行
GRANT SELECT, INSERT, UPDATE, DELETE ON member_note TO aifam_app;

-- 4. 平台审计表：append-only（BUG-011 / BUG-015）—— 独立隔离，app 角色仅 INSERT+SELECT
CREATE TABLE IF NOT EXISTS audit_log (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  family_member_id text NOT NULL,
  actor text NOT NULL,
  action text NOT NULL,
  detail jsonb,
  at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS audit_member_read ON audit_log;
CREATE POLICY audit_member_read ON audit_log
  FOR SELECT USING (family_member_id = app_current_member());
DROP POLICY IF EXISTS audit_insert ON audit_log;
CREATE POLICY audit_insert ON audit_log
  FOR INSERT WITH CHECK (true);                            -- 谁都能写审计（不可读他人）
-- 仅授 INSERT + SELECT；显式不授 UPDATE/DELETE → app 角色无法改/删审计（append-only）
REVOKE ALL ON audit_log FROM aifam_app;
GRANT SELECT, INSERT ON audit_log TO aifam_app;
