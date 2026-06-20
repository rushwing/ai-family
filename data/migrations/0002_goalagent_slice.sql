-- 0002_goalagent_slice —— REQ-003 WP-1：GoalAgent 业务表 + 平台状态表迁移 + RLS 内建
-- （BUG-002 / BUG-014 / BUG-011）。承 0001_rls_foundation 的 RLS 约定。
-- 幂等：可重复执行（IF EXISTS / IF NOT EXISTS / CREATE OR REPLACE / DROP POLICY IF EXISTS）。
--
-- 约定（同 0001）：
--   * 应用以非超级、无 BYPASSRLS 的 aifam_app 访问；每事务注入 set_config('app.member_id', <uid>, true)。
--   * 所有 tenant-bearing 表（业务 + 平台状态）ENABLE + FORCE RLS + member 隔离策略。
--   * 平台审计 audit.event：独立 schema + append-only（仅 INSERT+SELECT，无 UPDATE/DELETE）。

-- 0. 基座兜底（若 0001 未先行应用，仍可独立运行）
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aifam_app') THEN
    CREATE ROLE aifam_app NOLOGIN;
  END IF;
END $$;
CREATE OR REPLACE FUNCTION app_current_member() RETURNS text
  LANGUAGE sql STABLE AS $$ SELECT current_setting('app.member_id', true) $$;

-- ─────────────────────────── 业务表（member 隔离） ───────────────────────────

CREATE TABLE IF NOT EXISTS target (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  title text NOT NULL,
  subject text,
  status text NOT NULL DEFAULT 'active'
);
ALTER TABLE target ENABLE ROW LEVEL SECURITY;
ALTER TABLE target FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON target;
CREATE POLICY member_isolation ON target
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON target TO aifam_app;

CREATE TABLE IF NOT EXISTS plan (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  target_id bigint NOT NULL REFERENCES target(id),
  title text NOT NULL,
  status text NOT NULL DEFAULT 'active'
);
ALTER TABLE plan ENABLE ROW LEVEL SECURITY;
ALTER TABLE plan FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON plan;
CREATE POLICY member_isolation ON plan
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON plan TO aifam_app;

CREATE TABLE IF NOT EXISTS weekly_milestone (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  plan_id bigint NOT NULL REFERENCES plan(id),
  week_number int NOT NULL DEFAULT 1,
  title text NOT NULL
);
ALTER TABLE weekly_milestone ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_milestone FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON weekly_milestone;
CREATE POLICY member_isolation ON weekly_milestone
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON weekly_milestone TO aifam_app;

CREATE TABLE IF NOT EXISTS task (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  milestone_id bigint NOT NULL REFERENCES weekly_milestone(id),
  title text NOT NULL
);
ALTER TABLE task ENABLE ROW LEVEL SECURITY;
ALTER TABLE task FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON task;
CREATE POLICY member_isolation ON task
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON task TO aifam_app;

CREATE TABLE IF NOT EXISTS check_in (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  task_id bigint NOT NULL REFERENCES task(id),
  status text NOT NULL DEFAULT 'completed'
);
ALTER TABLE check_in ENABLE ROW LEVEL SECURITY;
ALTER TABLE check_in FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON check_in;
CREATE POLICY member_isolation ON check_in
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON check_in TO aifam_app;

CREATE TABLE IF NOT EXISTS report (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  report_type text NOT NULL DEFAULT 'weekly',
  content_md text NOT NULL DEFAULT ''
);
ALTER TABLE report ENABLE ROW LEVEL SECURITY;
ALTER TABLE report FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON report;
CREATE POLICY member_isolation ON report
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON report TO aifam_app;

-- ──────────────────── 平台状态表（tenant-bearing · member 隔离） ────────────────────

CREATE TABLE IF NOT EXISTS lg_checkpoint (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  thread_id text NOT NULL,
  checkpoint jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE lg_checkpoint ENABLE ROW LEVEL SECURITY;
ALTER TABLE lg_checkpoint FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON lg_checkpoint;
CREATE POLICY member_isolation ON lg_checkpoint
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON lg_checkpoint TO aifam_app;

CREATE TABLE IF NOT EXISTS outbox (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  idempotency_key text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON outbox;
CREATE POLICY member_isolation ON outbox
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON outbox TO aifam_app;

CREATE TABLE IF NOT EXISTS confirm_token (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  token text NOT NULL,
  tool text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz
);
ALTER TABLE confirm_token ENABLE ROW LEVEL SECURITY;
ALTER TABLE confirm_token FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON confirm_token;
CREATE POLICY member_isolation ON confirm_token
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON confirm_token TO aifam_app;

CREATE TABLE IF NOT EXISTS tool_call_log (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  tool text NOT NULL,
  at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE tool_call_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_call_log FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON tool_call_log;
CREATE POLICY member_isolation ON tool_call_log
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON tool_call_log TO aifam_app;

-- ──────────── 平台审计：独立 schema + append-only（BUG-011 / BUG-015） ────────────

CREATE SCHEMA IF NOT EXISTS audit;
GRANT USAGE ON SCHEMA audit TO aifam_app;

CREATE TABLE IF NOT EXISTS audit.event (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  actor text NOT NULL,
  action text NOT NULL,
  detail jsonb,
  at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE audit.event ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.event FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS audit_member_read ON audit.event;
CREATE POLICY audit_member_read ON audit.event
  FOR SELECT USING (family_member_id = app_current_member());
DROP POLICY IF EXISTS audit_insert ON audit.event;
CREATE POLICY audit_insert ON audit.event
  FOR INSERT WITH CHECK (family_member_id = app_current_member());
-- append-only：仅 INSERT + SELECT，显式不授 UPDATE/DELETE
REVOKE ALL ON audit.event FROM aifam_app;
GRANT SELECT, INSERT ON audit.event TO aifam_app;

-- 序列 USAGE（bigserial 自增；aifam_app 无 BYPASSRLS，需序列权限）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aifam_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO aifam_app;
