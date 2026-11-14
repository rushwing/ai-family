-- REQ-040: bounded append-only home evidence; no raw request/credentials/arguments.
-- Ordered after 0004; repeatable without rewriting/deleting existing evidence.
CREATE TABLE IF NOT EXISTS audit.home_action_event (
  event_id uuid PRIMARY KEY,
  attempt_id uuid NOT NULL,
  schema_version smallint NOT NULL DEFAULT 1 CHECK (schema_version = 1),
  family_member_id text CHECK (length(family_member_id) BETWEEN 1 AND 256),
  at timestamptz NOT NULL DEFAULT clock_timestamp(),
  key_id text NOT NULL CHECK (key_id ~ '^[A-Za-z0-9._:-]{1,64}$'),
  phase text NOT NULL CHECK (phase IN ('confirmation', 'execution', 'task')),
  outcome text NOT NULL CHECK (outcome IN ('started', 'allowed', 'denied', 'unavailable')),
  reason text NOT NULL CHECK (reason IN
    ('started', 'accepted', 'rejected', 'boundary_unavailable', 'interrupted')),
  http_status smallint CHECK (http_status BETWEEN 100 AND 599),
  duration_ms integer NOT NULL CHECK (duration_ms BETWEEN 0 AND 86400000),
  requester_ref text CHECK (requester_ref ~ '^[0-9a-f]{64}$'),
  home_ref text CHECK (home_ref ~ '^[0-9a-f]{64}$'),
  device_ref text CHECK (device_ref ~ '^[0-9a-f]{64}$'),
  capability_ref text CHECK (capability_ref ~ '^[0-9a-f]{64}$'),
  action_ref text CHECK (action_ref ~ '^[0-9a-f]{64}$'),
  task_ref text CHECK (task_ref ~ '^[0-9a-f]{64}$'),
  trace_ref text CHECK (trace_ref ~ '^[0-9a-f]{64}$'),
  idempotency_ref text CHECK (idempotency_ref ~ '^[0-9a-f]{64}$'),
  CHECK ((outcome = 'started' AND reason = 'started' AND http_status IS NULL)
    OR (outcome = 'allowed' AND reason = 'accepted')
    OR (outcome = 'denied' AND reason = 'rejected')
    OR (outcome = 'unavailable' AND reason IN ('boundary_unavailable', 'interrupted')))
);
ALTER TABLE audit.home_action_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.home_action_event FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS home_audit_insert ON audit.home_action_event;
CREATE POLICY home_audit_insert ON audit.home_action_event
  FOR INSERT TO aifam_app WITH CHECK
  (family_member_id IS NOT DISTINCT FROM nullif(app_current_member(), ''));
DROP POLICY IF EXISTS home_audit_read ON audit.home_action_event;
CREATE POLICY home_audit_read ON audit.home_action_event
  FOR SELECT TO aifam_app, aifam_kid USING
  (family_member_id = nullif(app_current_member(), ''));
DROP POLICY IF EXISTS home_audit_oversight ON audit.home_action_event;
CREATE POLICY home_audit_oversight ON audit.home_action_event
  FOR SELECT TO aifam_audit_reader USING (true);
REVOKE ALL ON audit.home_action_event FROM PUBLIC, aifam_app, aifam_kid, aifam_audit_reader;
GRANT USAGE ON SCHEMA audit TO aifam_app, aifam_kid, aifam_audit_reader;
GRANT INSERT, SELECT ON audit.home_action_event TO aifam_app;
GRANT SELECT ON audit.home_action_event TO aifam_kid, aifam_audit_reader;
CREATE INDEX IF NOT EXISTS home_action_member_time
  ON audit.home_action_event (family_member_id, at DESC, event_id DESC);
CREATE INDEX IF NOT EXISTS home_action_attempt
  ON audit.home_action_event (attempt_id);
