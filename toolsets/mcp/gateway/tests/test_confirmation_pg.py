"""REQ-003 durable shared confirmations: real PG, never SQLite/mock substitution."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest

from gateway.persistence import ConfirmationUnavailable, PostgresConfirmStore, ProofReplay


def binding(**changes):
    return (
        dict(
            member="A",
            session="session-a",
            tool="create_target",
            params={"title": "fixture", "idempotency_key": "fixture-1"},
        )
        | changes
    )


def issue(store, *, nonce=None, **changes):
    return store.issue_confirmed(
        **binding(**changes), nonce=nonce or uuid.uuid4().hex, timestamp=int(time.time())
    )


def test_restart_and_replay(pg_dsn):
    token = issue(PostgresConfirmStore(pg_dsn))
    store = PostgresConfirmStore(pg_dsn)
    assert store.consume(token, **binding()) is True
    assert PostgresConfirmStore(pg_dsn).consume(token, **binding()) is False


@pytest.mark.parametrize(
    "change",
    [
        {"member": "B"},
        {"session": "session-b"},
        {"tool": "delete_target"},
        {"params": {"title": "changed", "idempotency_key": "fixture-1"}},
    ],
)
def test_exact_binding_denies_without_consuming(pg_dsn, change):
    store = PostgresConfirmStore(pg_dsn)
    token = issue(store)
    assert store.consume(token, **binding(**change)) is False
    assert store.consume(token, **binding()) is True


def test_concurrent_consumption_one_winner(pg_dsn):
    token = issue(PostgresConfirmStore(pg_dsn))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(lambda _: PostgresConfirmStore(pg_dsn).consume(token, **binding()), range(16))
        )
    assert results.count(True) == 1
    assert results.count(False) == 15


def test_concurrent_proof_claim_one_token(pg_dsn):
    nonce = uuid.uuid4().hex

    def attempt(_):
        try:
            return issue(PostgresConfirmStore(pg_dsn), nonce=nonce)
        except ProofReplay:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(attempt, range(16)))
    assert sum(t is not None for t in tokens) == 1
    token = next(t for t in tokens if t)
    assert PostgresConfirmStore(pg_dsn).consume(token, **binding())


def test_proof_replay_after_new_process(pg_dsn):
    nonce = uuid.uuid4().hex
    token = issue(PostgresConfirmStore(pg_dsn), nonce=nonce)
    # No inherited Python dictionary. DSN/token are stdin, never argv or logs.
    script = """import json, sys
from gateway.persistence import PostgresConfirmStore, ProofReplay
v=json.load(sys.stdin)
s=PostgresConfirmStore(v["dsn"])
try:
 s.issue_confirmed(**v["binding"],nonce=v["nonce"],timestamp=v["timestamp"])
except ProofReplay:
 pass
else:
 raise AssertionError("proof replay minted another token")
assert s.consume(v["token"],**v["binding"])
assert not s.consume(v["token"],**v["binding"])
"""
    import json

    result = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(
            {
                "dsn": pg_dsn,
                "binding": binding(),
                "nonce": nonce,
                "timestamp": int(time.time()),
                "token": token,
            }
        ),
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, "independent confirmation process failed"


def test_expiry_and_database_clock(pg_dsn):
    store = PostgresConfirmStore(pg_dsn)
    with pytest.raises(ProofReplay):
        store.issue_confirmed(**binding(), nonce=uuid.uuid4().hex, timestamp=0)
    with pytest.raises(ProofReplay):
        store.issue_confirmed(
            **binding(), nonce=uuid.uuid4().hex, timestamp=int(time.time()) + 3600
        )
    token = issue(store)
    with psycopg.connect(pg_dsn) as conn:
        conn.execute(
            "UPDATE confirm_token SET expires_at = now() - interval '1 second' WHERE token = %s",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )
    assert store.consume(token, **binding()) is False


def test_issue_failure_rolls_back_nonce(pg_dsn):
    nonce = uuid.uuid4().hex
    with psycopg.connect(pg_dsn) as conn:
        conn.execute(
            "CREATE FUNCTION reject_fixture_issue() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN RAISE EXCEPTION 'fixture failure'; END $$"
        )
        conn.execute(
            "CREATE TRIGGER reject_fixture BEFORE INSERT ON confirm_token "
            "FOR EACH ROW EXECUTE FUNCTION reject_fixture_issue()"
        )
    try:
        with pytest.raises(ConfirmationUnavailable, match="^confirmation_unavailable$"):
            issue(PostgresConfirmStore(pg_dsn), nonce=nonce)
    finally:
        with psycopg.connect(pg_dsn) as conn:
            conn.execute("DROP TRIGGER reject_fixture ON confirm_token")
            conn.execute("DROP FUNCTION reject_fixture_issue()")
    # Same proof can be retried after a rolled-back transaction; no orphan claim.
    assert issue(PostgresConfirmStore(pg_dsn), nonce=nonce).startswith("cf_")


def test_rls_raw_token_privacy_and_checkin_compatibility(pg_dsn):
    store = PostgresConfirmStore(pg_dsn)
    token = issue(store)
    with psycopg.connect(pg_dsn) as conn:
        conn.execute(
            "INSERT INTO confirm_token (family_member_id,token,tool,task_id) "
            "VALUES ('A','checkin-fixture','checkin_task',123)"
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM confirm_token WHERE token = %s", (token,)
            ).fetchone()[0]
            == 0
        )
        conn.execute("SET LOCAL ROLE aifam_app")
        conn.execute("SELECT set_config('app.member_id','B',true)")
        assert (
            conn.execute(
                "SELECT count(*) FROM confirm_token WHERE family_member_id='A'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM gateway_confirmation_nonce WHERE family_member_id='A'"
            ).fetchone()[0]
            == 0
        )
        conn.execute("SELECT set_config('app.member_id','A',true)")
        assert (
            conn.execute(
                "SELECT count(*) FROM confirm_token WHERE token='checkin-fixture' "
                "AND task_id=123 AND gateway_version IS NULL"
            ).fetchone()[0]
            == 1
        )
    assert not store.consume("checkin-fixture", **binding(tool="checkin_task"))


def test_database_unavailable_is_redacted():
    store = PostgresConfirmStore("host=/tmp/req004-no-postgres dbname=private_fixture")
    assert "private_fixture" not in repr(store)
    with pytest.raises(ConfirmationUnavailable, match="^confirmation_unavailable$") as caught:
        issue(store)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("operation", ["issue", "consume"])
@pytest.mark.parametrize("stage", ["connect", "setup", "query", "commit"])
def test_database_value_errors_are_redacted(monkeypatch, operation, stage):
    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            if stage == "commit":
                raise ValueError("private database commit details")

        def execute(self, query, params=None):
            if stage == "setup" or (stage == "query" and not query.startswith(("SET", "SELECT"))):
                raise ValueError("private database query details")
            return self

        def fetchone(self):
            return (1,)

    def connect(*args, **kwargs):
        if stage == "connect":
            raise ValueError("private database connection details")
        return Connection()

    monkeypatch.setattr(psycopg, "connect", connect)
    store = PostgresConfirmStore("dbname=private_fixture")
    with pytest.raises(ConfirmationUnavailable, match="^confirmation_unavailable$") as caught:
        if operation == "issue":
            issue(store)
        else:
            store.consume("cf_fixture", **binding())
    assert caught.value.__cause__ is None
