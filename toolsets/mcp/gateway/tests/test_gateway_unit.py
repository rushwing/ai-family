"""Fast, service-free regressions for the WP-4 trust boundary."""

import time

import jwt
from fastapi.testclient import TestClient

import gateway.app as gateway_app
import gateway.auth as gateway_auth
from gateway.confirm import ConfirmStore
from gateway.interaction import sign_interaction

_CONFIRM_SECRET = "test-chatui-bff-secret-at-least-32-bytes"


def _claims(token: str | None) -> dict:
    identities = {
        "adult-a": {"role": "adult", "family_member_id": "A", "sid": "session-a"},
        "adult-a-2": {
            "role": "adult",
            "family_member_id": "A",
            "sid": "session-a-2",
        },
        "adult-b": {"role": "adult", "family_member_id": "B", "sid": "session-b"},
        "kid-b": {"role": "kid", "family_member_id": "B", "sid": "session-b"},
        "admin-z": {"role": "admin", "family_member_id": "Z", "sid": "session-z"},
    }
    if token not in identities:
        raise gateway_auth.AuthenticationError("bad token")
    return identities[token]


def _headers(identity: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {identity}"}


def _client(monkeypatch, executor=None) -> TestClient:
    monkeypatch.setattr(gateway_app, "verify_bearer", _claims)
    return TestClient(
        gateway_app.create_app(executor=executor, confirmation_secret=_CONFIRM_SECRET)
    )


def _confirm(client, identity: str, tool: str, params: dict, nonce: str) -> str:
    claims = _claims(identity)
    timestamp = int(time.time())
    signature = sign_interaction(
        _CONFIRM_SECRET,
        timestamp=timestamp,
        nonce=nonce,
        session=claims["sid"],
        member=claims["family_member_id"],
        tool=tool,
        params=params,
    )
    response = client.post(
        f"/confirmations/{tool}",
        json=params,
        headers={
            **_headers(identity),
            "X-AI-Family-Interaction-Timestamp": str(timestamp),
            "X-AI-Family-Interaction-Nonce": nonce,
            "X-AI-Family-Interaction-Signature": signature,
        },
    )
    assert response.status_code == 200
    return response.json()["confirm_token"]


def test_default_app_fails_closed_without_executor(monkeypatch):
    client = _client(monkeypatch)
    response = client.post("/tools/list_targets", json={}, headers=_headers("adult-a"))
    assert response.status_code == 503
    assert response.json()["error"] == "executor_unavailable"
    assert client.get("/readyz").status_code == 503


def test_confirmation_is_bound_to_exact_business_payload(monkeypatch):
    calls = []

    def execute(tool, member, params):
        calls.append((tool, member, params))
        return {"accepted": True}

    client = _client(monkeypatch, execute)
    params = {"title": "safe", "idempotency_key": "idem-1"}
    token = _confirm(
        client, "adult-a", "create_target", params, "nonce-payload-test"
    )

    changed = client.post(
        "/tools/create_target",
        json={"confirm_token": token, "title": "EVIL", "idempotency_key": "idem-1"},
        headers=_headers("adult-a"),
    )
    assert changed.status_code == 400
    assert not calls

    accepted = client.post(
        "/tools/create_target",
        json={"confirm_token": token, "title": "safe", "idempotency_key": "idem-1"},
        headers=_headers("adult-a"),
    )
    assert accepted.status_code == 200
    assert calls == [
        ("create_target", "A", {"title": "safe", "idempotency_key": "idem-1"})
    ]
    assert client.post(
        "/tools/create_target",
        json={"confirm_token": token, "title": "safe", "idempotency_key": "idem-1"},
        headers=_headers("adult-a"),
    ).status_code == 400


def test_confirmation_cannot_be_reused_for_another_tool(monkeypatch):
    client = _client(monkeypatch, lambda *_: {"accepted": True})
    token = _confirm(
        client, "adult-a", "create_target", {"title": "safe"}, "nonce-tool-test-1"
    )
    response = client.post(
        "/tools/update_target",
        json={"confirm_token": token, "title": "safe"},
        headers=_headers("adult-a"),
    )
    assert response.status_code == 400


def test_ordinary_agent_channel_cannot_mint_confirmation(monkeypatch):
    client = _client(monkeypatch, lambda *_: {"accepted": True})
    response = client.post(
        "/tools/create_target",
        json={"prepare": True, "title": "agent-chosen"},
        headers=_headers("adult-a"),
    )
    assert response.status_code == 403
    assert response.json()["error"] == "use_user_confirmation_channel"

    unsigned = client.post(
        "/confirmations/create_target",
        json={"title": "agent-chosen"},
        headers=_headers("adult-a"),
    )
    assert unsigned.status_code == 403


def test_interaction_proof_and_confirm_token_are_session_bound(monkeypatch):
    client = _client(monkeypatch, lambda *_: {"accepted": True})
    params = {"title": "safe"}
    token = _confirm(
        client,
        "adult-a",
        "create_target",
        params,
        "nonce-session-bound",
    )
    response = client.post(
        "/tools/create_target",
        json={"confirm_token": token, **params},
        headers=_headers("adult-a-2"),
    )
    assert response.status_code == 400


def test_interaction_proof_nonce_cannot_be_replayed(monkeypatch):
    client = _client(monkeypatch, lambda *_: {"accepted": True})
    claims = _claims("adult-a")
    timestamp = int(time.time())
    params = {"title": "safe"}
    nonce = "nonce-replay-proof"
    signature = sign_interaction(
        _CONFIRM_SECRET,
        timestamp=timestamp,
        nonce=nonce,
        session=claims["sid"],
        member=claims["family_member_id"],
        tool="create_target",
        params=params,
    )
    headers = {
        **_headers("adult-a"),
        "X-AI-Family-Interaction-Timestamp": str(timestamp),
        "X-AI-Family-Interaction-Nonce": nonce,
        "X-AI-Family-Interaction-Signature": signature,
    }
    assert client.post(
        "/confirmations/create_target", json=params, headers=headers
    ).status_code == 200
    assert client.post(
        "/confirmations/create_target", json=params, headers=headers
    ).status_code == 403


def test_audit_is_member_scoped_except_for_admin(monkeypatch):
    client = _client(monkeypatch, lambda *_: {"accepted": True})
    for identity, other in (("adult-a", "B"), ("adult-b", "A")):
        response = client.post(
            "/tools/list_targets",
            json={"family_member_id": other},
            headers=_headers(identity),
        )
        assert response.status_code == 403

    own = client.get("/audit/recent", headers=_headers("adult-a")).json()
    assert own and {row["member"] for row in own} == {"A"}
    kid = client.get("/audit/recent", headers=_headers("kid-b")).json()
    assert kid and {row["member"] for row in kid} == {"B"}
    all_rows = client.get("/audit/recent", headers=_headers("admin-z")).json()
    assert {row["member"] for row in all_rows} == {"A", "B"}


def test_invalid_json_is_not_silently_coerced(monkeypatch):
    client = _client(monkeypatch, lambda *_: {})
    response = client.post(
        "/tools/list_targets",
        content="{not-json",
        headers={**_headers("adult-a"), "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_json"


def test_authentication_and_tool_probing_denials_are_audited(monkeypatch):
    client = _client(monkeypatch, lambda *_: {})
    assert client.post("/tools/list_targets", json={}).status_code == 401
    assert client.post(
        "/tools/list_targets", json={}, headers=_headers("invalid-bearer")
    ).status_code == 401
    assert client.post(
        "/tools/not_a_tool", json={}, headers=_headers("adult-a")
    ).status_code == 404
    rows = client.get("/audit/recent", headers=_headers("admin-z")).json()
    assert {row["reason"] for row in rows} >= {"unauthenticated", "unknown_tool"}


def test_confirm_store_is_bounded_and_expires(monkeypatch):
    store = ConfirmStore(ttl_seconds=1, max_entries=2)
    first = store.issue(member="A", session="S", tool="create_target", params={"title": "1"})
    store.issue(member="A", session="S", tool="create_target", params={"title": "2"})
    store.issue(member="A", session="S", tool="create_target", params={"title": "3"})
    assert len(store) == 2
    assert not store.consume(
        first, member="A", session="S", tool="create_target", params={"title": "1"}
    )

    now = time.time()
    monkeypatch.setattr("gateway.confirm.time.time", lambda: now)
    expiring = store.issue(
        member="A", session="S", tool="create_target", params={"title": "x"}
    )
    monkeypatch.setattr("gateway.confirm.time.time", lambda: now + 2)
    assert not store.consume(
        expiring,
        member="A",
        session="S",
        tool="create_target",
        params={"title": "x"},
    )


def test_role_mapping_is_deterministic_and_ambiguous_roles_fail_closed():
    claims = {"realm_access": {"roles": ["adult", "offline_access"]}}
    assert gateway_auth._map_role(claims) == "adult"
    try:
        gateway_auth._map_role({"realm_access": {"roles": ["adult", "kid"]}})
    except gateway_auth.AuthorizationError:
        pass
    else:
        raise AssertionError("multiple platform roles must fail closed")


def test_missing_canonical_member_claim_is_rejected(monkeypatch):
    class _Key:
        key = "unused"

    class _Jwks:
        def get_signing_key_from_jwt(self, token):
            return _Key()

    monkeypatch.setenv("AIFAMILY_OIDC_ISSUER", "https://issuer.example")
    monkeypatch.setattr(gateway_auth, "_jwks", lambda _: _Jwks())
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "subject-only",
            "preferred_username": "fallback-must-not-be-used",
            "role": "adult",
        },
    )
    try:
        gateway_auth.verify_bearer("header.payload.signature")
    except gateway_auth.AuthenticationError:
        pass
    else:
        raise AssertionError("family_member_id must be mandatory")
