"""REQ-040 durable home-boundary evidence. No dispatch or request-body storage.

The trusted composition supplies DB credentials, a private HMAC key and optional
oversight approval. Neither pseudonymous references nor audit rows grant action
permission. A started row without a terminal row is an interrupted/unknown attempt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from gateway.auth import AuthenticationError, AuthorizationError, verify_bearer

_KEY_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}", re.ASCII)
_REFS = ("requester", "home", "device", "capability", "action", "task", "trace", "idempotency")
_REASONS = {
    "started": frozenset({"started"}),
    "allowed": frozenset({"accepted"}),
    "denied": frozenset({"rejected"}),
    "unavailable": frozenset({"boundary_unavailable", "interrupted"}),
}


class AuditUnavailable(Exception):
    """Fixed failure without credentials, private DB errors or request text."""


class AuditDenied(Exception):
    """Unverified or unapproved reader."""


@dataclass(frozen=True, slots=True, repr=False)
class AuditAttempt:
    attempt_id: uuid.UUID
    member: str | None
    phase: str
    references: tuple[str | None, ...]

    def __repr__(self) -> str:
        return "AuditAttempt()"


class PostgresHomeAudit:
    def __init__(
        self,
        dsn: str,
        *,
        key: bytes,
        key_id: str,
        oversight_dsn: str | None = None,
        approve_oversight: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        if type(dsn) is not str or not dsn.strip():
            raise ValueError("audit_database_required")
        if type(key) is not bytes or not 32 <= len(key) <= 128:
            raise ValueError("audit_key_required")
        if type(key_id) is not str or _KEY_ID.fullmatch(key_id) is None:
            raise ValueError("audit_key_id_required")
        if (oversight_dsn is None) != (approve_oversight is None) or (
            oversight_dsn is not None
            and (
                type(oversight_dsn) is not str
                or not oversight_dsn.strip()
                or not callable(approve_oversight)
            )
        ):
            raise ValueError("audit_oversight_configuration_required")
        self._dsn, self._key, self._key_id = dsn, key, key_id
        self._oversight_dsn, self._approve = oversight_dsn, approve_oversight

    def __repr__(self) -> str:
        return "<PostgresHomeAudit>"

    def _reference(self, kind: str, value: object, member: str | None) -> str | None:
        if type(value) is not str or not value.strip() or len(value) > 256:
            return None
        try:
            encoded = json.dumps(
                [1, self._key_id, member, kind, value], ensure_ascii=True, separators=(",", ":")
            ).encode("ascii")
            return hmac.new(self._key, encoded, hashlib.sha256).hexdigest()
        except Exception:
            return None

    def attempt(
        self, bearer: str | None, params: object, *, phase: str, task_id: str | None = None
    ) -> AuditAttempt:
        """Build detached redacted data; task_id is trusted internal metadata only."""
        if phase not in {"confirmation", "execution", "task"}:
            raise ValueError("invalid_audit_phase")
        try:
            claims = verify_bearer(bearer)
            member = claims["family_member_id"]
            if type(member) is not str or not member.strip() or len(member) > 256:
                raise ValueError("invalid_member")
        except Exception:
            claims, member = {}, None
        values = params if type(params) is dict else {}
        fields = (
            claims.get("sub"),
            values.get("home_id"),
            values.get("device_id"),
            values.get("capability_id"),
            values.get("action_id"),
            task_id,
            values.get("trace_id"),
            values.get("idempotency_key"),
        )
        return AuditAttempt(
            uuid.uuid4(),
            member,
            phase,
            tuple(
                self._reference(kind, value, member)
                for kind, value in zip(_REFS, fields, strict=True)
            ),
        )

    @contextmanager
    def _transaction(
        self, member: str | None, *, oversight: bool = False
    ) -> Iterator[psycopg.Connection]:
        try:
            dsn = self._oversight_dsn if oversight else self._dsn
            if dsn is None:
                raise AuditUnavailable("audit_unavailable")
            with psycopg.connect(dsn, connect_timeout=5) as conn:
                conn.execute(
                    "SET LOCAL ROLE aifam_audit_reader" if oversight else "SET LOCAL ROLE aifam_app"
                )
                conn.execute("SET LOCAL search_path = public, pg_catalog")
                conn.execute("SET LOCAL statement_timeout = '5s'")
                conn.execute("SET LOCAL lock_timeout = '5s'")
                conn.execute("SELECT set_config('app.member_id', %s, true)", (member or "",))
                yield conn
        except Exception:
            raise AuditUnavailable("audit_unavailable") from None

    def record(
        self,
        attempt: AuditAttempt,
        *,
        outcome: str,
        reason: str,
        duration_ms: int = 0,
        http_status: int | None = None,
    ) -> uuid.UUID:
        """Commit one immutable event. No task/key deduplication or physical effects."""
        if (
            type(attempt) is not AuditAttempt
            or type(attempt.attempt_id) is not uuid.UUID
            or attempt.phase not in {"confirmation", "execution", "task"}
            or (
                attempt.member is not None
                and (
                    type(attempt.member) is not str
                    or not attempt.member.strip()
                    or len(attempt.member) > 256
                )
            )
            or len(attempt.references) != len(_REFS)
            or any(
                v is not None and (type(v) is not str or re.fullmatch(r"[0-9a-f]{64}", v) is None)
                for v in attempt.references
            )
            or type(outcome) is not str
            or outcome not in _REASONS
            or type(reason) is not str
            or reason not in _REASONS[outcome]
            or type(duration_ms) is not int
            or not 0 <= duration_ms <= 86400000
            or (
                http_status is not None
                and (type(http_status) is not int or not 100 <= http_status <= 599)
            )
            or (outcome == "started" and http_status is not None)
        ):
            raise ValueError("invalid_audit_event")
        event_id = uuid.uuid4()
        with self._transaction(attempt.member) as conn:
            conn.execute(
                "INSERT INTO audit.home_action_event "
                "(event_id,attempt_id,family_member_id,key_id,phase,outcome,reason,duration_ms,"
                "http_status,requester_ref,home_ref,device_ref,capability_ref,action_ref,"
                "task_ref,trace_ref,idempotency_ref) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    event_id,
                    attempt.attempt_id,
                    attempt.member,
                    self._key_id,
                    attempt.phase,
                    outcome,
                    reason,
                    duration_ms,
                    http_status,
                    *attempt.references,
                ),
            )
        return event_id

    def recent(
        self, bearer: str | None, *, limit: int = 50, oversight: bool = False
    ) -> list[dict[str, Any]]:
        """Original JWT only; admin never implies unapproved cross-member access."""
        if type(limit) is not int or not 1 <= limit <= 100 or type(oversight) is not bool:
            raise ValueError("invalid_audit_read")
        try:
            claims = verify_bearer(bearer)
        except (AuthenticationError, AuthorizationError):
            raise AuditDenied("audit_forbidden") from None
        member = claims.get("family_member_id")
        if type(member) is not str or not member.strip() or len(member) > 256:
            raise AuditDenied("audit_forbidden")
        if oversight:
            if claims.get("role") not in {"adult", "admin"} or self._approve is None:
                raise AuditDenied("audit_forbidden")
            try:
                approved = self._approve(dict(claims)) is True
            except Exception:
                raise AuditDenied("audit_forbidden") from None
            if not approved:
                raise AuditDenied("audit_forbidden")
        with self._transaction(member, oversight=oversight) as conn:
            rows = (
                conn.cursor(row_factory=dict_row)
                .execute(
                    "SELECT event_id,attempt_id,schema_version,at,key_id,phase,outcome,reason,"
                    "duration_ms,http_status,requester_ref,home_ref,device_ref,capability_ref,"
                    "action_ref,task_ref,trace_ref,idempotency_ref "
                    "FROM audit.home_action_event ORDER BY at DESC,event_id DESC LIMIT %s",
                    (limit,),
                )
                .fetchall()
            )
        return [
            dict(row)
            | {
                "event_id": str(row["event_id"]),
                "attempt_id": str(row["attempt_id"]),
                "at": row["at"].isoformat(),
            }
            for row in rows
        ]


def elapsed_ms(start: float) -> int:
    return min(86400000, max(0, int((time.monotonic() - start) * 1000)))
