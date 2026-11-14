"""REQ-004 proposed acceptance: registered tool auth and durable gateway composition."""

from __future__ import annotations

import time
import uuid
from dataclasses import replace
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from goal_mcp import RegistrationError, ToolRegistry, fixture_tool

import gateway.auth as auth
from gateway.app import create_app
from gateway.interaction import sign_interaction
from gateway.persistence import PostgresConfirmStore
from gateway.tools import HOME_ACTION_TOOL, AuthenticatedTool, ToolDenied, gateway_registry

SECRET = "fixture-bff-secret-at-least-thirty-two-bytes"
ISSUER = "https://fixture.invalid/realm"


@pytest.fixture
def signed_identity(monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Actual RS256 verification; fixture key retrieval replaces external JWKS I/O.
    client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private.public_key())
    )
    monkeypatch.setattr(auth, "_jwks", lambda _: client)
    monkeypatch.setenv("AIFAMILY_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("AIFAMILY_OIDC_AUD", "fixture-audience")

    def mint(**changes):
        claims = {
            "sub": "fixture-subject",
            "family_member_id": "A",
            "role": "adult",
            "sid": "session-a",
            "aud": "fixture-audience",
            "iss": ISSUER,
            "exp": int(time.time()) + 300,
        } | changes
        return jwt.encode(claims, private, algorithm="RS256")

    return mint


def headers(token):
    return {"authorization": "Bearer " + token}


def proof_headers(token, params, *, nonce=None, member="A", session="session-a"):
    stamp = int(time.time())
    nonce = nonce or uuid.uuid4().hex
    return headers(token) | {
        "x-ai-family-interaction-timestamp": str(stamp),
        "x-ai-family-interaction-nonce": nonce,
        "x-ai-family-interaction-signature": sign_interaction(
            SECRET,
            timestamp=stamp,
            nonce=nonce,
            session=session,
            member=member,
            tool=HOME_ACTION_TOOL,
            params=params,
        ),
    }


def home_handler(dsn, calls, policy=lambda c, p: p.get("home_id") == "home-fixture"):
    def handler(claims, params, conn):
        # The actual DB connection must enforce transaction-local member scope.
        assert conn.execute("SELECT current_user, app_current_member()").fetchone() == (
            "aifam_app",
            claims["family_member_id"],
        )
        calls.append((claims["family_member_id"], params))
        return {"accepted": True}

    return AuthenticatedTool(
        gateway_registry().get(HOME_ACTION_TOOL), dsn=dsn, policy=policy, handler=handler
    )


def test_home_registered_but_unwired_and_memory_only_fail_closed(signed_identity):
    spec = gateway_registry().get(HOME_ACTION_TOOL)
    assert spec.risk == "write" and spec.roles == frozenset({"adult", "admin"})
    assert spec.manifest["auth"] == "oidc-jwt"
    calls = []
    client = TestClient(create_app(executor=lambda *a: calls.append(a)))
    for route in ("tools", "confirmations"):
        response = client.post(
            f"/{route}/{HOME_ACTION_TOOL}",
            json={"home_id": "home-fixture"},
            headers=headers(signed_identity()),
        )
        assert response.status_code == 503
    assert calls == []


@pytest.mark.parametrize(
    "field,value", [("auth", None), ("auth", "trust-agent"), ("test_ref", None), ("test_ref", "")]
)
@pytest.mark.parametrize("risk", ["read", "write", "high"])
def test_registration_requires_auth_and_test_reference(field, value, risk):
    spec = fixture_tool(risk="write" if risk == "high" else risk)
    spec = replace(spec, risk=risk, manifest=spec.manifest | {field: value})
    with pytest.raises(RegistrationError):
        ToolRegistry().register(spec)


def test_high_risk_cannot_drop_confirmation_metadata():
    spec = fixture_tool()
    ToolRegistry().register(replace(spec, risk="high"))
    with pytest.raises(RegistrationError):
        ToolRegistry().register(
            replace(spec, risk="high", manifest=spec.manifest | {"two_phase": False})
        )


@pytest.mark.parametrize(
    "identity",
    [
        None,
        "garbage",
        {"role": "kid"},
        {"family_member_id": "B"},
        {"exp": 0},
        {"aud": "wrong"},
        {"iss": "https://wrong.invalid"},
    ],
)
def test_tool_side_auth_zero_handler_calls(pg_dsn, signed_identity, identity):
    calls = []
    tool = home_handler(pg_dsn, calls)
    bearer = signed_identity(**identity) if isinstance(identity, dict) else identity
    params = {"home_id": "home-fixture", "family_member_id": "A"}
    with pytest.raises(ToolDenied):
        tool(bearer, params)
    assert calls == []


def test_persisted_home_confirmation_across_apps(pg_dsn, signed_identity):
    calls = []
    tool = home_handler(pg_dsn, calls)
    token = signed_identity()
    params = {"home_id": "home-fixture", "device_id": "device-fixture", "value": False}

    def client():
        return TestClient(
            create_app(
                confirmation_secret=SECRET,
                confirmation_store=PostgresConfirmStore(pg_dsn),
                home_tool=tool,
            )
        )

    first, second = client(), client()
    # Agent bearer and prepare cannot mint user confirmation.
    assert (
        first.post(
            f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=headers(token)
        ).status_code
        == 403
    )
    assert (
        first.post(
            f"/tools/{HOME_ACTION_TOOL}", json=params | {"prepare": True}, headers=headers(token)
        ).status_code
        == 403
    )
    proof = proof_headers(token, params)
    response = first.post(f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof)
    assert response.status_code == 200
    cf = response.json()["confirm_token"]
    assert calls == []
    # Same proof cannot mint a second token on another app or freshly constructed app.
    for app in (second, client()):
        assert (
            app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof).status_code
            == 403
        )
    # Changed business data must not consume the original confirmation.
    assert (
        second.post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=params | {"value": True, "confirm_token": cf},
            headers=headers(token),
        ).status_code
        == 400
    )
    response = second.post(
        f"/tools/{HOME_ACTION_TOOL}", json=params | {"confirm_token": cf}, headers=headers(token)
    )
    assert response.status_code == 200
    assert calls == [("A", params)]
    assert (
        client()
        .post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=params | {"confirm_token": cf},
            headers=headers(token),
        )
        .status_code
        == 400
    )
    assert len(calls) == 1


def test_current_policy_rechecked_before_consume_and_handler(pg_dsn, signed_identity):
    calls = []
    allowed = [True]
    tool = home_handler(pg_dsn, calls, policy=lambda c, p: allowed[0])
    client = TestClient(
        create_app(
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(pg_dsn),
            home_tool=tool,
        )
    )
    params, token = {"home_id": "home-fixture"}, signed_identity()
    response = client.post(
        f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof_headers(token, params)
    )
    assert response.status_code == 200
    allowed[0] = False
    cf = response.json()["confirm_token"]
    assert (
        client.post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=params | {"confirm_token": cf},
            headers=headers(token),
        ).status_code
        == 403
    )
    assert calls == []
    allowed[0] = True
    assert (
        client.post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=params | {"confirm_token": cf},
            headers=headers(token),
        ).status_code
        == 200
    )


def test_database_outage_no_fallback_or_secret_error(pg_dsn, signed_identity, monkeypatch):
    calls = []
    store = PostgresConfirmStore("host=/tmp/req004-no-postgres dbname=private_fixture")
    client = TestClient(
        create_app(
            confirmation_secret=SECRET,
            confirmation_store=store,
            home_tool=home_handler(pg_dsn, calls),
        )
    )
    token, params = signed_identity(), {"home_id": "home-fixture"}
    for route, body, hdr in [
        ("confirmations", params, proof_headers(token, params)),
        ("tools", params | {"confirm_token": "cf_fixture"}, headers(token)),
    ]:
        response = client.post(f"/{route}/{HOME_ACTION_TOOL}", json=body, headers=hdr)
        assert response.status_code == 503
        assert response.json() == {"error": "confirmation_unavailable"}
        assert "private_fixture" not in response.text
    assert calls == []


def test_memory_confirmation_cannot_enable_home_tool(pg_dsn, signed_identity, monkeypatch):
    monkeypatch.delenv("AIFAMILY_GATEWAY_PG_DSN", raising=False)
    calls = []
    client = TestClient(
        create_app(confirmation_secret=SECRET, home_tool=home_handler(pg_dsn, calls))
    )
    token, params = signed_identity(), {"home_id": "home-fixture"}
    assert (
        client.post(
            f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof_headers(token, params)
        ).status_code
        == 503
    )
    assert calls == []


@pytest.mark.parametrize("kind", ["missing", "kid", "member", "home", "device", "signature"])
def test_http_denials_never_call_home_handler(pg_dsn, signed_identity, kind):
    calls = []
    def policy(c, p):
        return (p.get("home_id"), p.get("device_id")) == ("home-fixture", "device-fixture")
    tool = home_handler(pg_dsn, calls, policy=policy)
    client = TestClient(
        create_app(
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(pg_dsn),
            home_tool=tool,
        )
    )
    params = {"home_id": "home-fixture", "device_id": "device-fixture", "family_member_id": "A"}
    token = signed_identity(
        **(
            {"role": "kid"}
            if kind == "kid"
            else {"family_member_id": "B"}
            if kind == "member"
            else {}
        )
    )
    if kind in ("home", "device"):
        params[kind + "_id"] = "not-granted"
    if kind == "signature":
        # Structurally valid JWT with a different actual RSA signing key.
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        claims = jwt.decode(token, options={"verify_signature": False})
        token = jwt.encode(claims, other_key, algorithm="RS256")
    for route in ("confirmations", "tools"):
        hdr = proof_headers(token, params) if route == "confirmations" else headers(token)
        if kind == "missing":
            hdr.pop("authorization")
        response = client.post(f"/{route}/{HOME_ACTION_TOOL}", json=params, headers=hdr)
        assert response.status_code in (401, 403)
    assert calls == []


def test_member_transaction_isolation_and_detachment(pg_dsn, signed_identity):
    seen = []
    spec = gateway_registry().get(HOME_ACTION_TOOL)

    def policy(claims, params):
        params["body"] = "malicious-policy-mutation"
        claims["family_member_id"] = "other-member"
        return True

    def handler(claims, params, conn):
        conn.execute(
            "INSERT INTO member_note (family_member_id,body) VALUES (%s,%s)",
            (claims["family_member_id"], params["body"]),
        )
        rows = conn.execute("SELECT family_member_id,body FROM member_note").fetchall()
        seen.append(rows)
        return {"accepted": True}

    tool = AuthenticatedTool(spec, dsn=pg_dsn, policy=policy, handler=handler)
    spec.manifest["roles"] = frozenset()  # Wrapper owns a detached registration.
    params = {"body": "original-fixture"}
    for member in ("A", "B"):
        tool(signed_identity(family_member_id=member), params)
    assert params == {"body": "original-fixture"}
    assert seen == [[("A", "original-fixture")], [("B", "original-fixture")]]


def test_broken_policy_fails_closed(pg_dsn, signed_identity):
    calls = []

    def broken_policy(claims, params):
        raise RuntimeError("private-fixture-policy-error")

    tool = home_handler(pg_dsn, calls, policy=broken_policy)
    client = TestClient(
        create_app(
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(pg_dsn),
            home_tool=tool,
        )
    )
    params, token = {"home_id": "home-fixture"}, signed_identity()
    response = client.post(
        f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof_headers(token, params)
    )
    assert response.status_code == 503
    assert "private-fixture-policy-error" not in response.text
    assert calls == []


@pytest.mark.parametrize("broken", [False, True])
def test_policy_changes_at_tool_entry_fail_closed(pg_dsn, signed_identity, broken):
    calls, checks = [], []

    def policy(claims, params):
        checks.append(True)
        # Issuance and pre-consumption checks pass; tool entry checks again.
        if len(checks) < 3:
            return True
        if broken:
            raise RuntimeError("private-policy-failure")
        return False

    client = TestClient(
        create_app(
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(pg_dsn),
            home_tool=home_handler(pg_dsn, calls, policy=policy),
        )
    )
    params, token = {"home_id": "home-fixture"}, signed_identity()
    response = client.post(
        f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof_headers(token, params)
    )
    assert response.status_code == 200
    response = client.post(
        f"/tools/{HOME_ACTION_TOOL}",
        json=params | {"confirm_token": response.json()["confirm_token"]},
        headers=headers(token),
    )
    assert response.status_code == (503 if broken else 403)
    assert response.json() == {
        "error": "home_boundary_unavailable" if broken else "forbidden"
    }
    assert len(checks) == 3
    assert calls == []


@pytest.mark.parametrize("change", ["payload", "session", "member", "signature"])
def test_changed_user_proof_cannot_issue_token(pg_dsn, signed_identity, change):
    calls = []
    client = TestClient(
        create_app(
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(pg_dsn),
            home_tool=home_handler(pg_dsn, calls),
        )
    )
    params, token = {"home_id": "home-fixture", "value": False}, signed_identity()
    proof = proof_headers(token, params)
    body = params.copy()
    if change == "payload":
        body["value"] = True
    elif change in ("session", "member"):
        proof["authorization"] = "Bearer " + signed_identity(
            **({"sid": "different-session"} if change == "session" else {"family_member_id": "B"})
        )
    else:
        proof["x-ai-family-interaction-signature"] = "0" * 64
    response = client.post(f"/confirmations/{HOME_ACTION_TOOL}", json=body, headers=proof)
    assert response.status_code == 403
    assert response.json() == {"error": "user_confirmation_required"}
    assert calls == []
    # A failed proof must not claim the nonce or prevent the genuine approval.
    response = client.post(
        f"/confirmations/{HOME_ACTION_TOOL}", json=params, headers=proof_headers(
            token, params, nonce=proof["x-ai-family-interaction-nonce"]
        )
    )
    assert response.status_code == 200
