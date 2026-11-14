"""Installed audit smoke with real PG and RS256; checks survive python -O."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace


def check():
    import jwt
    import psycopg
    from cryptography.hazmat.primitives.asymmetric import rsa
    from fastapi.testclient import TestClient
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    import gateway.auth as auth
    import gateway.home_audit as runtime
    from gateway.app import create_app
    from gateway.home_audit import AuditDenied, PostgresHomeAudit
    from gateway.tools import HOME_ACTION_TOOL

    values = json.load(sys.stdin)
    root = Path(values["root"]).resolve()
    checks = 0

    def require(condition):
        nonlocal checks
        if not condition:
            raise RuntimeError("installed_audit_check_failed")
        checks += 1

    require(not Path(runtime.__file__).resolve().is_relative_to(root))
    database = "audit_installed_" + uuid.uuid4().hex
    admin_dsn = values["dsn"]
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    dsn = make_conninfo(admin_dsn, dbname=database)
    try:
        with psycopg.connect(dsn) as conn:
            for _ in range(2):
                for path in sorted((root / "data/migrations").glob("*.sql")):
                    conn.execute(path.read_text())
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        auth._jwks = lambda _: SimpleNamespace(
            get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private.public_key())
        )
        os.environ["AIFAMILY_OIDC_ISSUER"] = "https://fixture.invalid/realm"
        os.environ["AIFAMILY_OIDC_AUD"] = "fixture-audience"

        def token(member="A", role="adult"):
            return jwt.encode(
                {
                    "sub": "private-fixture-subject",
                    "family_member_id": member,
                    "role": role,
                    "sid": "private-session",
                    "iss": "https://fixture.invalid/realm",
                    "aud": "fixture-audience",
                    "exp": int(time.time()) + 300,
                },
                private,
                algorithm="RS256",
            )

        key = b"fictional-audit-key-with-at-least-32-bytes"
        store = PostgresHomeAudit(dsn, key=key, key_id="fixture-v1")
        require(repr(store) == "<PostgresHomeAudit>")
        params = {
            "home_id": "private-home",
            "device_id": "private-device",
            "arguments": {"secret": "private-arguments"},
            "trace_id": "private-trace",
        }
        attempt = store.attempt(token(), params, phase="task", task_id="private-task")
        first = store.record(attempt, outcome="started", reason="started")
        second = store.record(attempt, outcome="allowed", reason="accepted")
        require(first != second)
        records = PostgresHomeAudit(dsn, key=key, key_id="fixture-v1").recent(token())
        require(len(records) == 2)
        require(all(r["at"] and r["schema_version"] == 1 for r in records))
        require("private-" not in json.dumps(records))
        require(store.recent(token("B", "admin")) == [])
        denied = False
        try:
            store.recent(token(role="admin"), oversight=True)
        except AuditDenied:
            denied = True
        require(denied)
        oversight = PostgresHomeAudit(
            dsn,
            key=key,
            key_id="fixture-v1",
            oversight_dsn=dsn,
            approve_oversight=lambda claims: True,
        )
        require(len(oversight.recent(token("B", "admin"), oversight=True)) == 2)
        denied = False
        try:
            oversight.recent(token(role="kid"), oversight=True)
        except AuditDenied:
            denied = True
        require(denied)
        for role in ("aifam_app", "aifam_kid", "aifam_audit_reader"):
            for command in (
                "UPDATE audit.home_action_event SET reason='rejected'",
                "DELETE FROM audit.home_action_event",
                "TRUNCATE audit.home_action_event",
            ):
                with psycopg.connect(dsn) as conn:
                    conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                    rejected = False
                    try:
                        conn.execute(command)
                    except psycopg.errors.InsufficientPrivilege:
                        rejected = True
                    conn.rollback()
                    require(rejected)
        app = TestClient(create_app(home_audit=store))
        response = app.post(f"/tools/{HOME_ACTION_TOOL}", json=params)
        require(response.status_code == 401)
        require(len(store.recent(token())) == 2)  # anonymous evidence is not member-visible
        response = app.post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=params,
            headers={"authorization": "Bearer " + token()},
        )
        require(response.status_code == 503)
        require(store.recent(token(), limit=1)[0]["outcome"] == "unavailable")
        broken = PostgresHomeAudit(
            "host=/tmp/req040-no-database dbname=private_fixture", key=key, key_id="fixture-v1"
        )
        response = TestClient(create_app(home_audit=broken)).post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=params,
        )
        require(response.status_code == 503 and response.json() == {"error": "audit_unavailable"})
        with psycopg.connect(dsn) as conn:
            migration = root / "data/migrations/0007_home_action_audit.sql"
            conn.execute(migration.read_text())
            require(
                conn.execute(
                    "SELECT count(*) FROM audit.home_action_event WHERE attempt_id=%s",
                    (attempt.attempt_id,),
                ).fetchone()
                == (2,)
            )
        return {"checks": checks, "dispatch_enabled": False}
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
