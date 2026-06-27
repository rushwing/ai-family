-- 0004_audit_oversight —— REQ-003 WP-6：审计 append-only 家长监督 + 会话历史物理分离
-- （BUG-011 / BUG-015；kid 红线）。承 0001/0002：audit.event 已于 0002 建（独立 audit schema +
-- append-only：aifam_app 仅 INSERT/SELECT、无 UPDATE/DELETE + RLS）。幂等可重复执行。
--
-- 不变量：
--   * 审计（audit.event）与可删会话历史（chat.session_message）**物理分离**（不同 schema）。
--   * 任何角色（含 kid）无法 UPDATE/DELETE/TRUNCATE 审计行（仅 append）。
--   * kid 软删自己的会话**不触及**审计；家长审计只读角色仍可见 kid 的操作记录。
--   * 其它成员仍受读侧 RLS 隔离（仅监督角色跨成员读审计）。

-- 1. 角色：kid（受限）+ 审计只读监督（家长侧）
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aifam_kid') THEN
    CREATE ROLE aifam_kid NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aifam_audit_reader') THEN
    CREATE ROLE aifam_audit_reader NOLOGIN;
  END IF;
END $$;

-- 2. 会话历史：独立 chat schema（与 audit 物理分离），支持软删除（deleted_at）
CREATE SCHEMA IF NOT EXISTS chat;
GRANT USAGE ON SCHEMA chat TO aifam_app, aifam_kid;

CREATE TABLE IF NOT EXISTS chat.session_message (
  id bigserial PRIMARY KEY,
  family_member_id text NOT NULL,
  body text,
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE chat.session_message ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat.session_message FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON chat.session_message;
CREATE POLICY member_isolation ON chat.session_message
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
GRANT SELECT, INSERT, UPDATE, DELETE ON chat.session_message TO aifam_app;
GRANT SELECT, UPDATE ON chat.session_message TO aifam_kid;  -- kid 可读 / 软删自己的会话

-- 3. audit.event：家长监督只读（跨成员读全部审计——仅审计表、仅该角色）；kid 只读自己（不可改/删）
GRANT USAGE ON SCHEMA audit TO aifam_kid, aifam_audit_reader;
GRANT SELECT ON audit.event TO aifam_audit_reader;
GRANT SELECT ON audit.event TO aifam_kid;  -- 仅 SELECT：append-only 对 kid 同样不可 UPDATE/DELETE
DROP POLICY IF EXISTS audit_oversight ON audit.event;
CREATE POLICY audit_oversight ON audit.event
  FOR SELECT TO aifam_audit_reader USING (true);  -- 监督角色跨成员读审计（与 member 读策略 OR 合并）

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA chat TO aifam_app;
