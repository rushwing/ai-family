"""REQ-003 shared PG confirmations. No fallback, credential repr or payload storage.

Each operation uses a new transaction with SET LOCAL member scope. Signature
verification precedes issue_confirmed(); proof claim and token issue commit
in one transaction. Consuming a confirmation never promises executor success.
"""

from __future__ import annotations

import hashlib
import secrets
from contextlib import contextmanager

import psycopg

from gateway.confirm import payload_digest


class ConfirmationUnavailable(Exception):
    """Fixed public failure; never export database exception text or a DSN."""


class ProofReplay(Exception):
    """Proof already claimed or outside the database-clock validity window."""


class PostgresConfirmStore:
    def __init__(self, dsn: str, *, ttl_seconds: int = 300, proof_max_age: int = 60):
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("confirmation database required")
        if any(type(n) is not int or not 1 <= n <= 3600 for n in (ttl_seconds, proof_max_age)):
            raise ValueError("confirmation lifetime out of bounds")
        self._dsn = dsn
        self._ttl = ttl_seconds
        self._proof_max_age = proof_max_age

    def __repr__(self):
        return "<PostgresConfirmStore>"

    @contextmanager
    def _transaction(self, member: str):
        try:
            with psycopg.connect(self._dsn, connect_timeout=5) as conn:
                conn.execute("SET LOCAL ROLE aifam_app")
                conn.execute("SET LOCAL search_path = public, pg_catalog")
                conn.execute("SET LOCAL statement_timeout = '5s'")
                conn.execute("SET LOCAL lock_timeout = '5s'")
                conn.execute("SELECT set_config('app.member_id', %s, true)", (member,))
                yield conn
        except (ProofReplay, ValueError):
            raise
        except Exception:
            raise ConfirmationUnavailable("confirmation_unavailable") from None

    def issue_confirmed(
        self, *, member: str, session: str, tool: str, params: dict, nonce: str, timestamp: int
    ) -> str:
        """Trusted composition only: signature must already have been checked.

        No ordinary issue() API: every issuance requires a durable proof claim.
        Database time rechecks the timestamp after any connection/lock wait.
        """
        digest = payload_digest(params)
        token = "cf_" + secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        nonce_hash = hashlib.sha256(nonce.encode()).hexdigest()
        with self._transaction(member) as conn:
            row = conn.execute(
                "INSERT INTO gateway_confirmation_nonce (nonce_sha256, family_member_id) "
                "SELECT %s, %s WHERE abs(extract(epoch from clock_timestamp()) - %s) <= %s "
                "ON CONFLICT DO NOTHING RETURNING nonce_sha256",
                (nonce_hash, member, timestamp, self._proof_max_age),
            ).fetchone()
            if row is None:
                raise ProofReplay("user_confirmation_required")
            conn.execute(
                "INSERT INTO confirm_token "
                "(family_member_id, token, tool, expires_at, gateway_version, "
                "session_id, payload_sha256) "
                "VALUES (%s, %s, %s, clock_timestamp() + (%s * interval '1 second'), 1, %s, %s)",
                (member, token_hash, tool, self._ttl, session, digest),
            )
        return token

    def consume(
        self, token: str | None, *, member: str, session: str, tool: str, params: dict
    ) -> bool:
        if type(token) is not str or not token.startswith("cf_") or len(token) > 128:
            return False
        digest = payload_digest(params)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self._transaction(member) as conn:
            row = conn.execute(
                "UPDATE confirm_token SET consumed_at = clock_timestamp() "
                "WHERE gateway_version = 1 AND token = %s AND family_member_id = %s "
                "AND session_id = %s AND tool = %s AND payload_sha256 = %s "
                "AND consumed_at IS NULL AND expires_at > clock_timestamp() RETURNING id",
                (token_hash, member, session, tool, digest),
            ).fetchone()
        return row is not None
