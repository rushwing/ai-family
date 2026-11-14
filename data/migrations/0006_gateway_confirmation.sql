-- REQ-003 WP-4: shared durable gateway confirmations. Existing check-in rows
-- retain gateway_version NULL and their original token/task semantics.
ALTER TABLE confirm_token ADD COLUMN IF NOT EXISTS gateway_version integer;
ALTER TABLE confirm_token ADD COLUMN IF NOT EXISTS session_id text;
ALTER TABLE confirm_token ADD COLUMN IF NOT EXISTS payload_sha256 text;
CREATE UNIQUE INDEX IF NOT EXISTS gateway_confirmation_token_unique
  ON confirm_token (token) WHERE gateway_version = 1;

-- Never delete proof claims while a signed proof could be accepted again.
-- Cleanup is an operator task after its validity window, not capacity eviction.
CREATE TABLE IF NOT EXISTS gateway_confirmation_nonce (
  nonce_sha256 text PRIMARY KEY,
  family_member_id text NOT NULL,
  claimed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE gateway_confirmation_nonce ENABLE ROW LEVEL SECURITY;
ALTER TABLE gateway_confirmation_nonce FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS member_isolation ON gateway_confirmation_nonce;
CREATE POLICY member_isolation ON gateway_confirmation_nonce
  USING (family_member_id = app_current_member())
  WITH CHECK (family_member_id = app_current_member());
REVOKE ALL ON gateway_confirmation_nonce FROM PUBLIC;
GRANT SELECT, INSERT ON gateway_confirmation_nonce TO aifam_app;
