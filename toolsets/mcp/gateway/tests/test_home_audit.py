"""REQ-040 generator-proposed real-PG audit privacy, access and failure criteria."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from guard_fixtures import Environment, request
from psycopg import sql
from test_registered_home import SECRET, headers, home_handler, proof_headers
from test_registered_home import signed_identity as identity_fixture

from gateway.app import create_app
from gateway.home_audit import AuditDenied, AuditUnavailable, PostgresHomeAudit
from gateway.persistence import PostgresConfirmStore
from gateway.tools import HOME_ACTION_TOOL

signed_identity = identity_fixture
KEY = b"fictional-audit-key-with-at-least-32-bytes"


@pytest.fixture
def store(pg_dsn):
    return PostgresHomeAudit(pg_dsn, key=KEY, key_id="fixture-v1")


def rows(dsn, attempt_id):
    with psycopg.connect(dsn) as conn:
        return conn.execute(
            "SELECT outcome,reason,http_status FROM audit.home_action_event "
            "WHERE attempt_id=%s ORDER BY at,event_id",
            (attempt_id,),
        ).fetchall()


def client(dsn, store, calls):
    return TestClient(
        create_app(
            home_audit=store,
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(dsn),
            home_tool=home_handler(dsn, calls),
        )
    )


def test_durable_redacted_records_and_task_correlation(pg_dsn, store, signed_identity):
    token = signed_identity(family_member_id="audit-" + uuid.uuid4().hex)
    params = request() | {
        "arguments": {"private": "never-store"},
        "confirm_token": "private-confirmation",
        "task_id": "untrusted-task",
    }
    attempts = [
        store.attempt(token, params, phase="task", task_id="trusted-task") for _ in range(2)
    ]
    ids = [store.record(a, outcome="denied", reason="rejected", duration_ms=12) for a in attempts]
    assert ids[0] != ids[1] and attempts[0].attempt_id != attempts[1].attempt_id
    assert attempts[0].references == attempts[1].references
    restored = PostgresHomeAudit(pg_dsn, key=KEY, key_id="fixture-v1").recent(token)
    assert len(restored) == 2
    assert {r["event_id"] for r in restored} == {str(i) for i in ids}
    assert all(r["schema_version"] == 1 and r["duration_ms"] == 12 and r["at"] for r in restored)
    assert restored[0]["task_ref"] != store.attempt(token, params, phase="task").references[5]
    encoded = json.dumps(restored) + repr(store) + repr(attempts[0])
    for value in (
        token,
        "never-store",
        "private-confirmation",
        "untrusted-task",
        "trusted-task",
        "fixture-subject",
        params["home_id"],
        params["trace_id"],
        KEY.decode(),
    ):
        assert value not in encoded
    assert "family_member_id" not in restored[0]


@pytest.mark.parametrize(
    "field", ["home_id", "device_id", "capability_id", "action_id", "trace_id", "idempotency_key"]
)
@pytest.mark.parametrize("value", [None, {}, "", "x" * 257])
def test_malformed_references_are_omitted(store, signed_identity, field, value):
    attempt = store.attempt(signed_identity(), request(**{field: value}), phase="execution")
    index = {
        "home_id": 1,
        "device_id": 2,
        "capability_id": 3,
        "action_id": 4,
        "trace_id": 6,
        "idempotency_key": 7,
    }[field]
    assert attempt.references[index] is None


def test_domain_member_and_key_separation(pg_dsn, store, signed_identity):
    params = {
        k: "same"
        for k in (
            "home_id",
            "device_id",
            "capability_id",
            "action_id",
            "trace_id",
            "idempotency_key",
        )
    }
    a = store.attempt(signed_identity(), params, phase="task", task_id="same")
    b = store.attempt(signed_identity(family_member_id="B"), params, phase="task", task_id="same")
    changed = PostgresHomeAudit(pg_dsn, key=b"different-fixture-key-with-32-bytes", key_id="v2")
    c = changed.attempt(signed_identity(), params, phase="task", task_id="same")
    assert len(set(a.references[1:])) == 7
    assert all(x != y for x, y in zip(a.references, b.references, strict=True))
    assert all(x != y for x, y in zip(a.references, c.references, strict=True))


@pytest.mark.parametrize("kind", ["missing", "garbage", "expired", "issuer", "role"])
def test_unverified_identity_is_anonymous(pg_dsn, store, signed_identity, kind):
    token = (
        None
        if kind == "missing"
        else "bad-jwt"
        if kind == "garbage"
        else signed_identity(
            **{
                "expired": {"exp": 0},
                "issuer": {"iss": "https://wrong.invalid"},
                "role": {"role": "unrecognized"},
            }[kind]
        )
    )
    attempt = store.attempt(token, {"family_member_id": "A"}, phase="execution")
    assert attempt.member is None and attempt.references[0] is None
    store.record(attempt, outcome="denied", reason="rejected", http_status=401)
    assert all(r["attempt_id"] != str(attempt.attempt_id) for r in store.recent(signed_identity()))
    with pytest.raises(AuditDenied, match="^audit_forbidden$"):
        store.recent(token)


@pytest.mark.parametrize("role", ["adult", "admin", "kid"])
def test_member_scope_even_for_admin(pg_dsn, store, signed_identity, role):
    member = "reader-" + uuid.uuid4().hex
    token = signed_identity(family_member_id=member, role=role)
    a = store.attempt(token, request(), phase="execution")
    b = store.attempt(
        signed_identity(family_member_id="other-" + member), request(), phase="execution"
    )
    for attempt in (a, b):
        store.record(attempt, outcome="denied", reason="rejected")
    assert [r["attempt_id"] for r in store.recent(token)] == [str(a.attempt_id)]
    with pytest.raises(AuditDenied):
        store.recent(token, oversight=True)


@pytest.mark.parametrize("approved", [False, "true", 1, None, True])
def test_oversight_requires_explicit_exact_approval(pg_dsn, signed_identity, approved):
    store = PostgresHomeAudit(
        pg_dsn,
        key=KEY,
        key_id="fixture-v1",
        oversight_dsn=pg_dsn,
        approve_oversight=lambda c: approved,
    )
    attempt = store.attempt(None, {}, phase="execution")
    store.record(attempt, outcome="denied", reason="rejected")
    if approved is True:
        found = store.recent(signed_identity(role="admin"), oversight=True, limit=100)
        assert any(r["attempt_id"] == str(attempt.attempt_id) for r in found)
    else:
        with pytest.raises(AuditDenied):
            store.recent(signed_identity(role="admin"), oversight=True)
    with pytest.raises(AuditDenied):
        store.recent(signed_identity(role="kid"), oversight=True)


@pytest.mark.parametrize("role", ["aifam_app", "aifam_kid", "aifam_audit_reader"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "TRUNCATE"])
def test_append_only_privileges(pg_dsn, role, operation):
    commands = {
        "UPDATE": "UPDATE audit.home_action_event SET reason='rejected'",
        "DELETE": "DELETE FROM audit.home_action_event",
        "TRUNCATE": "TRUNCATE audit.home_action_event",
    }
    with psycopg.connect(pg_dsn) as conn:
        conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
        conn.execute("SELECT set_config('app.member_id','A',true)")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(commands[operation])
        conn.rollback()


def test_rls_cross_member_insert_default_scope_and_migration_preserves_rows(
    pg_dsn,
    store,
    signed_identity,
):
    attempt = store.attempt(signed_identity(), request(), phase="execution")
    event_id = store.record(attempt, outcome="denied", reason="rejected")
    root = Path(__file__).resolve().parents[4]
    with psycopg.connect(pg_dsn) as conn:
        assert conn.execute(
            "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
            "WHERE oid='audit.home_action_event'::regclass"
        ).fetchone() == (True, True)
        conn.execute((root / "data/migrations/0007_home_action_audit.sql").read_text())
        assert conn.execute(
            "SELECT count(*) FROM audit.home_action_event WHERE event_id=%s", (event_id,)
        ).fetchone() == (1,)
        conn.execute("SET LOCAL ROLE aifam_app")
        conn.execute("SELECT set_config('app.member_id','B',true)")
        assert conn.execute(
            "SELECT count(*) FROM audit.home_action_event WHERE event_id=%s", (event_id,)
        ).fetchone() == (0,)
        conn.rollback()
    # Explicit forged target member on the store's insertion transaction is rejected by PG.
    with store._transaction("B") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "INSERT INTO audit.home_action_event "
                "(event_id,attempt_id,family_member_id,key_id,phase,outcome,reason,duration_ms) "
                "VALUES (%s,%s,'A','fixture-v1','execution','started','started',0)",
                (uuid.uuid4(), uuid.uuid4()),
            )
        conn.rollback()
    with psycopg.connect(pg_dsn) as conn:
        conn.execute("SET LOCAL ROLE aifam_app")
        assert conn.execute("SELECT count(*) FROM audit.home_action_event").fetchone() == (0,)


@pytest.mark.parametrize("route", ["tools", "confirmations"])
@pytest.mark.parametrize("kind", ["allowed", "kid", "anonymous", "malformed"])
def test_http_attempts_record_actual_outcome(pg_dsn, store, signed_identity, route, kind):
    calls = []
    app = client(pg_dsn, store, calls)
    params = {"home_id": "home-fixture", "device_id": "private-device"}
    token = signed_identity(role="kid" if kind == "kid" else "adult")
    hdr = proof_headers(token, params) if route == "confirmations" else headers(token)
    if kind == "anonymous":
        hdr.pop("authorization")
    response = app.post(
        f"/{route}/{HOME_ACTION_TOOL}",
        content="{invalid" if kind == "malformed" else json.dumps(params),
        headers=hdr,
    )
    expected = (
        400
        if kind == "malformed"
        else 401
        if kind == "anonymous"
        else (403 if kind == "kid" else 200 if route == "confirmations" else 400)
    )
    assert response.status_code == expected
    with psycopg.connect(pg_dsn) as conn:
        data = conn.execute(
            "SELECT attempt_id FROM audit.home_action_event ORDER BY at DESC LIMIT 1"
        ).fetchone()
    result = rows(pg_dsn, data[0])
    assert result[0] == ("started", "started", None)
    assert result[1] == (
        ("allowed", "accepted", 200) if expected == 200 else ("denied", "rejected", expected)
    )
    assert calls == []


def install_reject_trigger(dsn, *, terminal_only=False):
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "CREATE FUNCTION reject_audit_fixture() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN RAISE EXCEPTION 'private-audit-database-failure'; END $$"
        )
        condition = " WHEN (NEW.outcome <> 'started')" if terminal_only else ""
        conn.execute(
            "CREATE TRIGGER reject_audit_fixture BEFORE INSERT ON audit.home_action_event "
            "FOR EACH ROW" + condition + " EXECUTE FUNCTION reject_audit_fixture()"
        )


def drop_reject_trigger(dsn):
    with psycopg.connect(dsn) as conn:
        conn.execute("DROP TRIGGER reject_audit_fixture ON audit.home_action_event")
        conn.execute("DROP FUNCTION reject_audit_fixture()")


@pytest.mark.parametrize("route", ["tools", "confirmations"])
@pytest.mark.parametrize("failure", ["database", "permission", "insert"])
def test_audit_failure_prevents_all_delegation(pg_dsn, store, signed_identity, route, failure):
    calls, policy = [], []
    tool = home_handler(pg_dsn, calls, policy=lambda c, p: policy.append(True) or True)
    if failure == "database":
        store = PostgresHomeAudit(
            "host=/tmp/req040-no-database dbname=private_fixture", key=KEY, key_id="fixture-v1"
        )
    elif failure == "permission":
        with psycopg.connect(pg_dsn) as conn:
            conn.execute("REVOKE INSERT ON audit.home_action_event FROM aifam_app")
    else:
        install_reject_trigger(pg_dsn)
    try:
        app = TestClient(
            create_app(
                home_audit=store,
                confirmation_secret=SECRET,
                home_tool=tool,
                confirmation_store=PostgresConfirmStore(pg_dsn),
            )
        )
        token, params = signed_identity(), {"home_id": "home-fixture"}
        response = app.post(
            f"/{route}/{HOME_ACTION_TOOL}", json=params, headers=proof_headers(token, params)
        )
        assert response.status_code == 503 and response.json() == {"error": "audit_unavailable"}
        assert calls == policy == []
        assert "private" not in response.text
    finally:
        if failure == "insert":
            drop_reject_trigger(pg_dsn)
        elif failure == "permission":
            with psycopg.connect(pg_dsn) as conn:
                conn.execute("GRANT INSERT ON audit.home_action_event TO aifam_app")


def test_terminal_failure_retains_started_and_does_not_retry(pg_dsn, store, signed_identity):
    calls = []
    install_reject_trigger(pg_dsn, terminal_only=True)
    token, params = signed_identity(), {"home_id": "home-fixture"}
    try:
        app = client(pg_dsn, store, calls)
        response = app.post(
            f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof_headers(token, params)
        )
        assert response.status_code == 503 and response.json() == {"error": "audit_unavailable"}
        latest = store.recent(token, limit=1)[0]
        assert rows(pg_dsn, latest["attempt_id"]) == [("started", "started", None)]
        assert calls == []
    finally:
        drop_reject_trigger(pg_dsn)


def test_guard_confirmation_consumption_and_rollback_survive_audit(pg_dsn, store, signed_identity):
    env = Environment(pg_dsn)
    app = TestClient(
        create_app(
            home_audit=store,
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(pg_dsn),
            home_tool=env.guard().as_tool(),
        )
    )
    token, params = signed_identity(), request()
    proof = proof_headers(token, params)
    response = app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof)
    assert response.status_code == 200
    body = params | {"confirm_token": response.json()["confirm_token"]}
    response = app.post(f"/tools/{HOME_ACTION_TOOL}", json=body, headers=headers(token))
    assert response.status_code == 503
    assert store.recent(token, limit=1)[0]["outcome"] == "unavailable"
    assert (
        app.post(f"/tools/{HOME_ACTION_TOOL}", json=body, headers=headers(token)).status_code == 400
    )
    assert (
        app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof).status_code
        == 403
    )


def test_concurrent_retries_append_and_process_restart_preserves_correlation(
    pg_dsn,
    store,
    signed_identity,
):
    token = signed_identity(family_member_id="concurrent-" + uuid.uuid4().hex)
    params = request()

    def append(_):
        attempt = store.attempt(token, params, phase="task", task_id="task-fixture")
        return store.record(attempt, outcome="denied", reason="rejected")

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(append, range(12)))
    assert len(set(ids)) == 12
    before = store.recent(token)
    assert len(before) == 12 and len({r["task_ref"] for r in before}) == 1
    script = """import json,sys
from gateway.home_audit import PostgresHomeAudit
v=json.load(sys.stdin)
s=PostgresHomeAudit(v['dsn'],key=v['key'].encode(),key_id='fixture-v1')
# Read under a real PG RLS transaction in a separate interpreter, no parent memory.
with s._transaction(v['member']) as c:
 rows=c.execute('SELECT task_ref,trace_ref,idempotency_ref FROM audit.home_action_event').fetchall()
if len(rows)!=12 or len(set(rows))!=1: raise RuntimeError('restart_evidence_failed')
print('restart_ok')
"""
    # Use the actual verified member, never decode JWT claims without verifying.
    attempt = store.attempt(token, params, phase="task")
    result = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        capture_output=True,
        timeout=20,
        input=json.dumps({"dsn": pg_dsn, "key": KEY.decode(), "member": attempt.member}),
    )
    assert result.returncode == 0 and result.stdout.strip() == "restart_ok"


@pytest.mark.parametrize(
    "change",
    [{"key": b"short"}, {"key_id": "private\nvalue"}, {"dsn": ""}, {"oversight_dsn": "fixture"}],
)
def test_invalid_configuration(change):
    with pytest.raises(ValueError):
        PostgresHomeAudit(**({"dsn": "fixture", "key": KEY, "key_id": "v1"} | change))


@pytest.mark.parametrize(
    "change",
    [
        {"duration_ms": True},
        {"http_status": 600},
        {"reason": "private-error"},
        {"outcome": "success"},
    ],
)
def test_invalid_record_vocabulary(store, signed_identity, change):
    attempt = store.attempt(signed_identity(), request(), phase="execution")
    with pytest.raises(ValueError, match="^invalid_audit_event$"):
        store.record(attempt, **({"outcome": "denied", "reason": "rejected"} | change))
    with pytest.raises(ValueError):
        store.record(
            replace(attempt, references=("raw-private-data",) * 8),
            outcome="denied",
            reason="rejected",
        )


@pytest.mark.parametrize("limit", [True, 0, 101, "10"])
def test_read_bounds(store, signed_identity, limit):
    with pytest.raises(ValueError, match="^invalid_audit_read$"):
        store.recent(signed_identity(), limit=limit)


def test_real_lock_timeout_releases_connection_and_prevents_delegation(
    pg_dsn,
    store,
    signed_identity,
):
    calls = []
    app = client(pg_dsn, store, calls)
    token, params = signed_identity(), {"home_id": "home-fixture"}
    proof = proof_headers(token, params)
    with psycopg.connect(pg_dsn) as blocker:
        blocker.execute("LOCK TABLE audit.home_action_event IN ACCESS EXCLUSIVE MODE")
        start = time.monotonic()
        response = app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof)
        assert response.status_code == 503 and response.json() == {"error": "audit_unavailable"}
        assert 4 <= time.monotonic() - start < 10
        assert calls == []
        blocker.rollback()
    # The failed audit did not claim the interaction proof; exact retry can proceed.
    assert (
        app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof).status_code
        == 200
    )


def test_missing_schema_fails_closed_and_recovers(pg_dsn, store, signed_identity):
    calls = []
    with psycopg.connect(pg_dsn) as conn:
        conn.execute("ALTER TABLE audit.home_action_event RENAME TO hidden_audit_fixture")
    try:
        response = client(pg_dsn, store, calls).post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=request(),
            headers=headers(signed_identity()),
        )
        assert response.status_code == 503 and response.json() == {"error": "audit_unavailable"}
        assert calls == []
    finally:
        with psycopg.connect(pg_dsn) as conn:
            conn.execute("ALTER TABLE audit.hidden_audit_fixture RENAME TO home_action_event")
    store.record(store.attempt(None, {}, phase="execution"), outcome="denied", reason="rejected")


def test_reader_database_and_approval_errors_are_fixed(pg_dsn, signed_identity):
    broken = PostgresHomeAudit(
        "host=/tmp/req040-no-database dbname=private_fixture", key=KEY, key_id="v1"
    )
    with pytest.raises(AuditUnavailable, match="^audit_unavailable$"):
        broken.recent(signed_identity())

    def reject(claims):
        raise RuntimeError("private-oversight-details")

    store = PostgresHomeAudit(
        pg_dsn, key=KEY, key_id="v1", oversight_dsn=pg_dsn, approve_oversight=reject
    )
    with pytest.raises(AuditDenied, match="^audit_forbidden$"):
        store.recent(signed_identity(role="admin"), oversight=True)


def test_unexpected_route_exception_is_recorded_without_private_text(
    pg_dsn,
    store,
    signed_identity,
    monkeypatch,
):
    tool = home_handler(pg_dsn, [])

    def broken(*args):
        raise RuntimeError("private-route-error")

    monkeypatch.setattr(tool, "authorize", broken)
    app = TestClient(
        create_app(
            home_audit=store, home_tool=tool, confirmation_store=PostgresConfirmStore(pg_dsn)
        )
    )
    token = signed_identity()
    response = app.post(f"/tools/{HOME_ACTION_TOOL}", json=request(), headers=headers(token))
    assert response.status_code == 503 and "private" not in response.text
    record = store.recent(token, limit=1)[0]
    assert record["outcome"] == "unavailable" and record["reason"] == "interrupted"


def test_oversized_body_and_response_never_store_payload(pg_dsn, store, signed_identity):
    token = signed_identity()
    response = client(pg_dsn, store, []).post(
        f"/tools/{HOME_ACTION_TOOL}",
        content="private" * 10000,
        headers=headers(token),
    )
    assert response.status_code == 400
    record = store.recent(token, limit=1)[0]
    assert record["outcome"] == "denied" and record["home_ref"] is None
    assert "private" not in json.dumps(record)
