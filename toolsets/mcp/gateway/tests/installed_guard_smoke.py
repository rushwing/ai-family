"""Installed-package guard check; -I and -O work, no pytest/source path imports."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace


def check():
    import goal_mcp
    import home_device_fabric.state_store as state_runtime
    import jwt
    import psycopg
    import state_schema.action_contracts as schema_runtime
    from cryptography.hazmat.primitives.asymmetric import rsa
    from fastapi.testclient import TestClient
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    import gateway.auth as auth
    import gateway.home_guard as runtime
    from gateway.app import create_app
    from gateway.interaction import sign_interaction
    from gateway.persistence import PostgresConfirmStore
    from gateway.tools import HOME_ACTION_TOOL

    values = json.load(sys.stdin)
    root = Path(values["root"]).resolve()
    checks = 0

    def require(condition):
        nonlocal checks
        if not condition:
            raise RuntimeError("installed_guard_check_failed")
        checks += 1

    for module in (runtime, state_runtime, schema_runtime, goal_mcp):
        require(not Path(module.__file__).resolve().is_relative_to(root))
    fixture_path = root / "toolsets/mcp/gateway/tests/guard_fixtures.py"
    spec = importlib.util.spec_from_file_location("guard_fixture", fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    database = "guard_installed_" + uuid.uuid4().hex
    admin_dsn = values["dsn"]
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    dsn = make_conninfo(admin_dsn, dbname=database)
    try:
        with psycopg.connect(dsn) as conn:
            for _ in range(2):
                for path in sorted((root / "data/migrations").glob("*.sql")):
                    conn.execute(path.read_text())
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        auth._jwks = lambda _: SimpleNamespace(
            get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key())
        )
        os.environ["AIFAMILY_OIDC_ISSUER"] = "https://fixture.invalid/realm"
        os.environ["AIFAMILY_OIDC_AUD"] = "fixture-audience"
        claims = {
            "sub": "fixture-subject",
            "family_member_id": "A",
            "role": "adult",
            "sid": "session-a",
            "aud": "fixture-audience",
            "iss": "https://fixture.invalid/realm",
            "exp": int(time.time()) + 300,
        }
        token = jwt.encode(claims, key, algorithm="RS256")
        env = fixture.Environment(dsn)
        guard, req = env.guard(), fixture.request()
        require(guard.assess(token, req).to_dict() == {"status": "eligible", "reason": None})
        require(guard.assess(None, req).reason == "unauthenticated")
        require(guard.assess(token, fixture.request(device_id="absent")).reason == "forbidden")
        env.authority.grant(fixture.request(device_id="absent"))
        require(
            guard.assess(token, fixture.request(device_id="absent")).reason == "guard_unavailable"
        )
        require(
            guard.assess(token, fixture.request(arguments={"is_on": 1})).reason
            == "invalid_arguments"
        )
        with env.store.capture_lease(
            fixture.context(), home_id=fixture.HOME, device_id="device-0"
        ) as capture:
            require(capture.version == 1 and capture.epoch == 1)
        expired = False
        try:
            _ = capture.epoch
        except state_runtime.StateStoreError:
            expired = True
        require(expired)
        env.clock[0] += 1001
        require(guard.assess(token, req).reason == "device_unavailable")
        env.clock[0] = fixture.NOW
        guard = env.guard()
        secret = "fixture-independent-bff-secret-at-least-32-bytes"
        app = TestClient(
            create_app(
                confirmation_secret=secret,
                confirmation_store=PostgresConfirmStore(dsn),
                home_tool=guard.as_tool(),
            )
        )
        hdr = {"authorization": "Bearer " + token}
        require(
            app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=hdr).status_code == 403
        )
        stamp, nonce = int(time.time()), uuid.uuid4().hex
        proof = hdr | {
            "x-ai-family-interaction-timestamp": str(stamp),
            "x-ai-family-interaction-nonce": nonce,
            "x-ai-family-interaction-signature": sign_interaction(
                secret,
                timestamp=stamp,
                nonce=nonce,
                session="session-a",
                member="A",
                tool=HOME_ACTION_TOOL,
                params=req,
            ),
        }
        issued = app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=proof)
        require(issued.status_code == 200)
        body = req | {"confirm_token": issued.json()["confirm_token"]}
        require(app.post(f"/tools/{HOME_ACTION_TOOL}", json=body, headers=hdr).status_code == 503)
        require(app.post(f"/tools/{HOME_ACTION_TOOL}", json=body, headers=hdr).status_code == 400)
        require(
            app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=proof).status_code
            == 403
        )
        env.authority.update(granted=False)
        require(guard.assess(token, req).reason == "forbidden")
        require(repr(guard) == "HomeActionGuard()")
        return {"checks": checks, "dispatch_enabled": False}
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
