"""REQ-039 generator-proposed criteria: real PG, signatures and fenced state."""

from __future__ import annotations

import copy
import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Event

import psycopg
import pytest
from fastapi.testclient import TestClient
from guard_fixtures import HOME, NOW, Environment, context, request, snapshot
from home_device_fabric.state_store import StateStoreError
from test_registered_home import SECRET, headers, proof_headers
from test_registered_home import signed_identity as identity_fixture

from gateway.app import create_app
from gateway.home_guard import GuardDecision, HomeActionGuard
from gateway.persistence import PostgresConfirmStore
from gateway.tools import HOME_ACTION_TOOL

signed_identity = identity_fixture


@pytest.fixture
def env(pg_dsn):
    return Environment(pg_dsn)


def result(guard, token, req=None):
    return guard.assess(token, request() if req is None else req).to_dict()


def expected(reason):
    return {
        "status": "unavailable" if reason == "guard_unavailable" else "rejected",
        "reason": reason,
    }


@pytest.mark.parametrize(
    "kind,reason",
    [
        ("missing", "unauthenticated"),
        ("garbage", "unauthenticated"),
        ("expired", "unauthenticated"),
        ("issuer", "unauthenticated"),
        ("audience", "unauthenticated"),
        ("kid", "forbidden"),
        ("member", "forbidden"),
        ("subject", "forbidden"),
        ("admin", "forbidden"),
        ("session", "session_required"),
        ("ambiguous", "session_required"),
        ("blank_subject", "unauthenticated"),
    ],
)
def test_identity_and_exact_grants(env, signed_identity, kind, reason):
    claims = {
        "expired": {"exp": 0},
        "issuer": {"iss": "https://wrong.invalid"},
        "audience": {"aud": "other"},
        "kid": {"role": "kid"},
        "member": {"family_member_id": "B"},
        "subject": {"sub": "other-subject"},
        "admin": {"role": "admin"},
        "session": {"sid": None},
        "ambiguous": {"session_state": "other-session"},
        "blank_subject": {"sub": " "},
    }.get(kind, {})
    token = (
        None if kind == "missing" else "garbage" if kind == "garbage" else signed_identity(**claims)
    )
    assert result(env.guard(), token) == expected(reason)


@pytest.mark.parametrize(
    "req",
    [
        request(home_id="home-absent"),
        request(device_id="device-absent"),
        request(action_id="toggle"),
        request(capability_id="vendor.custom"),
    ],
)
def test_pregrant_forbidden_without_descriptive_lookup(env, signed_identity, req, monkeypatch):
    from home_device_fabric.action_validation import ActionValidator

    def forbidden_lookup(*args):
        raise AssertionError("validator must not be consulted")

    monkeypatch.setattr(ActionValidator, "validate", forbidden_lookup)
    assert result(env.guard(), signed_identity(), req) == expected("forbidden")


@pytest.mark.parametrize("kind", ["home", "device", "generation", "binding"])
def test_postgrant_configuration_mismatch_is_unavailable(env, signed_identity, kind):
    req = request(
        **(
            {"home_id": "home-absent"}
            if kind == "home"
            else {"device_id": "device-absent"}
            if kind == "device"
            else {}
        )
    )
    env.authority.grant(req)
    if kind == "generation":
        env.authority.update(generation="generation-2")
    if kind == "binding":
        binding = copy.deepcopy(env.config["bindings"]["bindings"][0])
        binding["provider_instance_id"] = "ha-other"
        env.authority.update(binding=binding)
    assert result(env.guard(), signed_identity(), req) == expected("guard_unavailable")


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"device_id": "device-7"}, "capabilities_uninitialized"),
        ({"device_id": "device-6"}, "unknown_capability"),
        ({"capability_id": "vendor.custom"}, "unknown_capability"),
        ({"capability_version": 2}, "unsupported_capability_version"),
        (
            {
                "device_id": "device-2",
                "capability_id": "home.temperature_sensor",
                "action_id": "set_value",
            },
            "read_only_capability",
        ),
        ({"action_id": "toggle"}, "unknown_action"),
        ({"arguments": {"is_on": 1}}, "invalid_arguments"),
        ({"arguments": {"is_on": True, "extra": 0}}, "invalid_arguments"),
    ],
)
def test_authorized_semantic_reasons(env, signed_identity, changes, reason):
    req = request(**changes)
    env.authority.grant(req)
    assert result(env.guard(), signed_identity(), req) == expected(reason)


@pytest.mark.parametrize(
    "req",
    [
        [],
        {},
        request(family_member_id="A"),
        request(context={}),
        request(arguments=None),
        request(schema_version=True),
        request(arguments={"is_on": float("nan")}),
    ],
)
def test_structural_rejection_never_reads_authority(env, signed_identity, req):
    assert result(env.guard(), signed_identity(), req) == expected("invalid_request")
    assert env.authority.scopes == 0


def test_size_limit_and_configuration_detachment(env, signed_identity):
    assert result(env.guard(max_input_bytes=1), signed_identity()) == expected("input_too_large")
    guard = env.guard()
    payload = request()
    original = copy.deepcopy(payload)
    env.config["capabilities"].clear()
    assert result(guard, signed_identity(), payload) == {"status": "eligible", "reason": None}
    assert payload == original
    for value in (guard, guard.assess(signed_identity(), payload)):
        assert "fixture" not in repr(value)
        with pytest.raises(TypeError):
            pickle.dumps(value)
    decision = guard.assess(signed_identity(), payload)
    with pytest.raises(FrozenInstanceError):
        decision.reason = "forbidden"
    exported = decision.to_dict()
    exported["status"] = "rejected"
    assert decision.to_dict() == {"status": "eligible", "reason": None}


@pytest.mark.parametrize(
    "changes",
    [
        {"max_availability_age_ms": 0},
        {"max_availability_age_ms": True},
        {"scope_wait_seconds": 0},
        {"max_input_bytes": True},
        {"configuration_generation": ""},
        {"provider_instance_id": "https://private.invalid"},
        {"authority": object()},
        {"store": object()},
        {"clock": None},
    ],
)
def test_invalid_configuration_is_fixed(env, changes):
    with pytest.raises(ValueError, match="^invalid_guard_configuration$") as caught:
        env.guard(**changes)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


@pytest.mark.parametrize(
    "kind", ["distributed", "truthy", "principal", "target", "missing_field", "broken"]
)
def test_malformed_or_unsafe_authority_never_allows(env, signed_identity, kind):
    guard = env.guard()
    if kind == "distributed":
        env.authority.coordination = "distributed"

    def mutate(data):
        if kind == "truthy":
            data["granted"] = "true"
        elif kind == "principal":
            data["principal"]["family_member_id"] = "B"
        elif kind == "target":
            data["target"]["device_id"] = "device-1"
        elif kind == "missing_field":
            del data["binding"]
        elif kind == "broken":
            raise ValueError("private-authority-error")
        return data

    env.authority.mutate_result = mutate
    decision = result(guard, signed_identity())
    assert decision == expected("guard_unavailable")
    assert "private" not in json.dumps(decision)


@pytest.mark.parametrize(
    "kind",
    [
        "offline",
        "unknown",
        "stale",
        "future",
        "old",
        "epoch",
        "uninitialized",
        "missing_binding",
        "fresh_property_old_availability",
    ],
)
def test_availability_is_independently_fresh(env, signed_identity, kind):
    state = snapshot()
    if kind == "offline":
        state = snapshot(status="offline")
    elif kind == "unknown":
        state = snapshot(status="unknown")
    elif kind == "future":
        state = snapshot(stamp="2026-11-14T00:00:01Z")
    elif kind in ("old", "fresh_property_old_availability"):
        state = snapshot(stamp="2026-11-13T23:59:58Z")
        if kind == "fresh_property_old_availability":
            state["reported_state"] = {
                "is_on": {
                    "status": "known",
                    "value": True,
                    "observed_at": "2026-11-14T00:00:00Z",
                    "ordering": {"epoch": 1, "sequence": 2},
                }
            }
    elif kind == "epoch":
        env.store.advance_epoch(context(), home_id=HOME, epoch=2)
    elif kind == "stale":
        env.store.mark_home_stale(context(), home_id=HOME)
    elif kind == "uninitialized":
        from home_device_fabric.state_store import CurrentStateStore

        env.store = CurrentStateStore(
            inventories=[env.config["registered_inventory"]],
            grants=[context() | {"access": "write"}],
        )
        env.authority.store = env.store
    elif kind == "missing_binding":
        env.authority.mutate_result = lambda data: data | {"binding": None}
    if kind not in ("uninitialized",):
        env.store.put(
            context(),
            home_id=HOME,
            device_id="device-0",
            state=state,
            expected_revision=1,
            now_ms=NOW,
        )
    assert result(env.guard(), signed_identity()) == expected("device_unavailable")


def test_availability_age_boundaries_and_clock_regression(env, signed_identity):
    guard = env.guard()
    token = signed_identity()
    env.clock[0] = NOW + 1000
    assert result(guard, token) == {"status": "eligible", "reason": None}
    env.clock[0] += 1
    assert result(guard, token) == expected("device_unavailable")
    env.clock[0] = NOW
    assert result(guard, token) == expected("guard_unavailable")
    assert result(env.guard(clock=lambda: True), token) == expected("guard_unavailable")


def test_valid_curtain_and_admin_require_exact_grants(env, signed_identity):
    req = request(
        device_id="device-1",
        capability_id="home.positionable",
        action_id="set_position",
        arguments={"position_percent": 100},
    )
    assert result(env.guard(), signed_identity(), req) == {"status": "eligible", "reason": None}
    env.authority.grant(request(), role="admin")
    assert result(env.guard(), signed_identity(role="admin")) == {
        "status": "eligible",
        "reason": None,
    }


def test_capture_expiry_release_and_timeout(env):
    from home_device_fabric.state_store import CurrentStateStore

    args = dict(home_id=HOME, device_id="device-0", timeout_seconds=1)
    with env.store.capture_lease(context(), **args) as capture:
        assert capture.version == 1 and capture.epoch == 1
        assert capture.view(now_ms=NOW, max_age_ms=1000).freshness == "fresh"
        with pytest.raises(StateStoreError, match="scope_timeout"):
            with env.store.capture_lease(context(), **args):
                pass
        with pytest.raises(TypeError):
            pickle.dumps(capture)
    with pytest.raises(StateStoreError, match="expired_capture"):
        _ = capture.epoch
    with pytest.raises(RuntimeError):
        with env.store.capture_lease(context(), **args):
            raise RuntimeError("fixture")
    assert type(env.store) is CurrentStateStore
    assert (
        env.store.read(
            context(), home_id=HOME, device_id="device-0", now_ms=NOW, max_age_ms=1000
        ).freshness
        == "fresh"
    )


@pytest.mark.parametrize("writer", ["put", "apply", "epoch", "stale", "reconcile", "rebuild"])
def test_all_state_writers_participate_in_capture_barrier(env, writer):
    started = Event()

    def write():
        started.set()
        if writer == "put":
            return env.store.put(
                context(),
                home_id=HOME,
                device_id="device-0",
                state=snapshot(),
                expected_revision=1,
                now_ms=NOW,
            )
        if writer == "apply":
            return env.store.apply(
                context(),
                home_id=HOME,
                device_id="device-0",
                event=snapshot(sequence=2),
                now_ms=NOW,
            )
        if writer == "epoch":
            return env.store.advance_epoch(context(), home_id=HOME, epoch=2)
        if writer == "stale":
            return env.store.mark_home_stale(context(), home_id=HOME)
        if writer == "reconcile":
            return env.store.reconcile_home(
                context(),
                home_id=HOME,
                epoch=2,
                baseline_states={
                    "schema_version": 1,
                    "states": [snapshot(f"device-{i}", epoch=2, sequence=0) for i in range(8)],
                },
                buffered_events=[],
                now_ms=NOW,
            )
        return env.store.rebuild(
            context(),
            home_id=HOME,
            states={"schema_version": 1, "states": [snapshot(f"device-{i}") for i in range(8)]},
            now_ms=NOW,
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with env.store.capture_lease(context(), home_id=HOME, device_id="device-0"):
            future = pool.submit(write)
            assert started.wait(2)
            assert not future.done()
        if writer == "rebuild":
            with pytest.raises(StateStoreError, match="already_initialized"):
                future.result(timeout=5)
        else:
            future.result(timeout=5)


def client(env, **kwargs):
    return TestClient(
        create_app(
            confirmation_secret=SECRET,
            confirmation_store=PostgresConfirmStore(env.dsn),
            home_tool=env.guard().as_tool(),
            **kwargs,
        )
    )


def confirm(app, token, req):
    response = app.post(
        f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=proof_headers(token, req)
    )
    assert response.status_code == 200, response.text
    return req | {"confirm_token": response.json()["confirm_token"]}


def test_registered_eligibility_never_dispatches_or_claims_success(env, signed_identity):
    calls = []
    app = client(env, executor=lambda *a: calls.append(a))
    token = signed_identity()
    req = request()
    assert (
        app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=headers(token)).status_code
        == 403
    )
    body = confirm(app, token, req)
    response = app.post(f"/tools/{HOME_ACTION_TOOL}", json=body, headers=headers(token))
    assert response.status_code == 503 and response.json() == {"error": "home_boundary_unavailable"}
    assert (
        app.post(f"/tools/{HOME_ACTION_TOOL}", json=body, headers=headers(token)).status_code == 400
    )
    assert calls == []


@pytest.mark.parametrize("change", ["revoke", "rebind", "generation", "disconnect"])
def test_final_entry_rechecks_after_preflight_and_burns_token(
    env, signed_identity, change, monkeypatch
):
    effects = []
    monkeypatch.setattr(
        HomeActionGuard,
        "_disabled_entry",
        staticmethod(lambda: effects.append(True) or {"fixture": True}),
    )

    def mutate(count):
        if count != 4:
            return
        if change == "revoke":
            env.authority.update(granted=False)
        elif change == "generation":
            env.authority.update(generation="generation-2")
        elif change == "disconnect":
            env.store.mark_home_stale(context(), home_id=HOME)
        else:
            binding = copy.deepcopy(env.config["bindings"]["bindings"][0])
            binding["mapping"]["entity_ids"] = ["switch.replaced"]
            env.authority.update(binding=binding)

    env.authority.before_scope = mutate
    app = client(env)
    token = signed_identity()
    body = confirm(app, token, request())
    response = app.post(f"/tools/{HOME_ACTION_TOOL}", json=body, headers=headers(token))
    assert response.status_code == (403 if change in ("revoke", "disconnect") else 503)
    assert effects == []
    # Policy may now fail before consume: inspect durable storage directly.
    assert not PostgresConfirmStore(env.dsn).consume(
        body["confirm_token"],
        member="A",
        session="session-a",
        tool=HOME_ACTION_TOOL,
        params=request(),
    )


def test_preflight_invalid_request_does_not_consume_confirmation(env, signed_identity):
    app = client(env)
    token = signed_identity()
    body = confirm(app, token, request())
    invalid = body | {"arguments": {"is_on": 1}}
    assert (
        app.post(f"/tools/{HOME_ACTION_TOOL}", json=invalid, headers=headers(token)).status_code
        == 403
    )
    assert PostgresConfirmStore(env.dsn).consume(
        body["confirm_token"],
        member="A",
        session="session-a",
        tool=HOME_ACTION_TOOL,
        params=request(),
    )


def test_real_pg_and_state_updates_wait_for_final_lease(env, signed_identity, monkeypatch):
    entered, release, updating = Event(), Event(), Event()
    effects = []

    def terminal():
        entered.set()
        if not release.wait(5):
            raise RuntimeError("fixture barrier timeout")
        effects.append(True)
        return {"fixture_only": True}

    monkeypatch.setattr(HomeActionGuard, "_disabled_entry", staticmethod(terminal))
    app = client(env)
    token = signed_identity()
    body = confirm(app, token, request())
    writer_pid = []

    def update():
        with psycopg.connect(env.dsn) as conn:
            writer_pid.append(conn.info.backend_pid)
            updating.set()
            env.authority.update(granted=False, connection=conn)
            env.store.mark_home_stale(context(), home_id=HOME)

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempt = pool.submit(
            app.post, f"/tools/{HOME_ACTION_TOOL}", json=body, headers=headers(token)
        )
        try:
            assert entered.wait(5)
            writer = pool.submit(update)
            assert updating.wait(2)
            # Query PG's actual lock dependency, not a timing guess.
            blocked = False
            with psycopg.connect(env.dsn) as conn:
                for _ in range(1000):
                    if conn.execute(
                        "SELECT cardinality(pg_blocking_pids(%s))", (writer_pid[0],)
                    ).fetchone()[0]:
                        blocked = True
                        break
            assert blocked and not writer.done()
        finally:
            release.set()
        assert attempt.result(timeout=5).status_code == 200  # fixture sink only
        writer.result(timeout=5)
    assert effects == [True]
    assert result(env.guard(), token) == expected("forbidden")


def test_guard_decision_rejects_unknown_reason():
    for status, reason in (
        ("rejected", "unknown_device"),
        ("eligible", "forbidden"),
        ("unavailable", "private"),
    ):
        with pytest.raises(ValueError, match="invalid_guard_decision"):
            GuardDecision(status, reason)


@pytest.mark.parametrize("kind", ["descriptor", "action"])
def test_initial_allowlist_rejects_forged_or_extra_actions(env, signed_identity, kind):
    descriptor = env.config["capabilities"][0]["capabilities"][0]
    req = request()
    if kind == "descriptor":
        descriptor["title"] = "Replacement"
    else:
        descriptor["actions"]["toggle"] = copy.deepcopy(descriptor["actions"]["set_on"])
        req = request(action_id="toggle")
        env.authority.grant(req)
    assert result(env.guard(), signed_identity(), req) == expected("unsupported_action")


def test_tampered_signature_is_not_a_trusted_context(env, signed_identity):
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    token = signed_identity()
    claims = jwt.decode(token, options={"verify_signature": False})
    forged = jwt.encode(
        claims, rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm="RS256"
    )
    assert result(env.guard(), forged) == expected("unauthenticated")
    assert result(env.guard(), claims) == expected("unauthenticated")
    assert env.authority.scopes == 0


def test_missing_capture_api_and_database_outage_fail_closed(env, signed_identity, monkeypatch):
    from home_device_fabric.state_store import CurrentStateStore

    guard = env.guard()
    monkeypatch.setattr(CurrentStateStore, "capture_lease", None)
    assert result(guard, signed_identity()) == expected("guard_unavailable")

    def failed(*args, **kwargs):
        raise ValueError("private DSN fixture detail")

    monkeypatch.setattr(psycopg, "connect", failed)
    assert result(guard, signed_identity()) == expected("guard_unavailable")


def test_pg_scope_wait_is_bounded(env, signed_identity):
    from psycopg import sql

    guard = env.guard(scope_wait_seconds=1)
    with psycopg.connect(env.dsn) as blocker:
        blocker.execute(
            sql.SQL("UPDATE {} SET granted=granted").format(sql.Identifier(env.authority.table))
        )
        assert result(guard, signed_identity()) == expected("guard_unavailable")
    assert result(guard, signed_identity()) == {"status": "eligible", "reason": None}


def test_shared_confirmation_replay_and_changed_payload_across_apps(env, signed_identity):
    first, second = client(env), client(env)
    token, req = signed_identity(), request()
    proof = proof_headers(token, req)
    altered = req | {"arguments": {"is_on": False}}
    assert (
        first.post(f"/confirmations/{HOME_ACTION_TOOL}", json=altered, headers=proof).status_code
        == 403
    )
    issued = first.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=proof)
    assert issued.status_code == 200
    assert (
        second.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=proof).status_code
        == 403
    )
    cf = issued.json()["confirm_token"]
    assert (
        second.post(
            f"/tools/{HOME_ACTION_TOOL}",
            json=altered | {"confirm_token": cf},
            headers=headers(token),
        ).status_code
        == 400
    )
    # Valid original remains consumable; concurrently exactly one reaches the
    # deliberately disabled final entry. Every other attempt is replay-denied.
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(
                lambda _: (
                    client(env)
                    .post(
                        f"/tools/{HOME_ACTION_TOOL}",
                        json=req | {"confirm_token": cf},
                        headers=headers(token),
                    )
                    .status_code
                ),
                range(8),
            )
        )
    assert results.count(503) == 1 and results.count(400) == 7


def test_grant_denial_does_not_claim_interaction_proof(env, signed_identity):
    app, token, req = client(env), signed_identity(), request()
    proof = proof_headers(token, req)
    env.authority.update(granted=False)
    assert (
        app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=proof).status_code == 403
    )
    env.authority.update(granted=True)
    assert (
        app.post(f"/confirmations/{HOME_ACTION_TOOL}", json=req, headers=proof).status_code == 200
    )


def test_post_wait_clock_is_used_and_missing_epoch_denies(env, signed_identity):
    from home_device_fabric.state_store import CurrentStateStore

    guard = env.guard()
    env.authority.after_lock = lambda _: env.clock.__setitem__(0, NOW + 1001)
    assert result(guard, signed_identity()) == expected("device_unavailable")
    env.authority.after_lock = lambda _: None
    env.clock[0] = NOW
    store = CurrentStateStore(
        inventories=[env.config["registered_inventory"]], grants=[context() | {"access": "write"}]
    )
    store.rebuild(
        context(),
        home_id=HOME,
        states={"schema_version": 1, "states": [snapshot(f"device-{i}") for i in range(8)]},
        now_ms=NOW,
    )
    env.store = store
    env.authority.store = store
    assert result(env.guard(), signed_identity()) == expected("device_unavailable")


def test_token_expiry_after_scope_wait_is_denied(env, signed_identity, monkeypatch):
    import time

    import gateway.home_guard as module

    token = signed_identity()
    later = time.time() + 600
    env.authority.after_lock = lambda _: monkeypatch.setattr(module.time, "time", lambda: later)
    assert result(env.guard(), token) == expected("unauthenticated")
