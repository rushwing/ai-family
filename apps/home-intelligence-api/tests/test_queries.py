"""REQ-035 HTTP boundary assertions with real RSA tokens and canonical runtime."""

import json
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fixtures import claims, context, state, token
from home_device_fabric.home_queries import HomeQueryService
from home_intelligence_api import TokenVerifier, create_app
from home_intelligence_api.auth import AuthenticationError
from starlette.testclient import TestClient

PATHS = ["/api/home", "/api/areas", "/api/devices", "/api/twin/snapshot", "/api/devices/device-one"]


def get(setup, path="/api/home", query="home_id=home-example", **kwargs):
    return setup["client"].get(
        path + ("?" + query if query else ""),
        headers=kwargs.pop("headers", setup["headers"]),
        **kwargs,
    )


def error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json() == {"error": {"code": code}}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    if status == 401:
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.tc035_01
def test_literal_home_areas_devices(setup):
    assert get(setup).json() == {
        "status": "found",
        "data": {
            "id": "home-example",
            "name": "Fictional",
            "residence_type": "apartment",
        },
    }
    areas = get(setup, "/api/areas")
    assert areas.status_code == 200
    assert areas.json() == {
        "status": "found",
        "data": [
            {
                "id": area,
                "home_id": "home-example",
                "name": "Fictional area",
                "area_type": "living_room",
                "floor_id": None,
                "labels": [],
                "aliases": [],
            }
            for area in ("area-empty", "area-main")
        ],
    }
    devices = get(setup, "/api/devices")
    assert devices.status_code == 200
    assert devices.json() == {
        "status": "found",
        "data": [
            {
                "id": "device-one",
                "home_id": "home-example",
                "name": "Fictional device",
                "area_id": "area-main",
                "labels": [],
            },
            {
                "id": "device-two",
                "home_id": "home-example",
                "name": "Fictional device",
                "area_id": None,
                "labels": [],
            },
        ],
    }


@pytest.mark.tc035_01
def test_snapshot_and_detail_match_projections(setup):
    snap = get(setup, "/api/twin/snapshot")
    assert snap.status_code == 200, snap.text
    data = snap.json()["data"]
    assert set(data) == {"home", "areas", "devices", "states"}
    for name, route in [
        ("home", "/api/home"),
        ("areas", "/api/areas"),
        ("devices", "/api/devices"),
    ]:
        assert data[name] == get(setup, route).json()["data"]
    assert [v["state"]["device_id"] for v in data["states"]] == ["device-one", "device-two"]
    detail = get(setup, "/api/devices/device-one")
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"] == {
        "device": data["devices"][0],
        "state": data["states"][0],
        "capabilities": {"status": "found", "data": []},
    }
    assert get(setup, "/api/devices/device-two").json()["data"]["capabilities"] == {
        "status": "uninitialized",
        "data": None,
    }
    for forbidden in ("entity_id", "provider_instance_id", "access_token", "binding"):
        assert forbidden not in snap.text and forbidden not in detail.text


@pytest.mark.tc035_01
@pytest.mark.parametrize("area,expected", [("area-main", ["device-one"]), ("area-empty", [])])
def test_area_filter(setup, area, expected):
    response = get(setup, "/api/devices", "home_id=home-example&area_id=" + area)
    assert response.status_code == 200
    assert [d["id"] for d in response.json()["data"]] == expected


@pytest.mark.tc035_02
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize(
    "authorization", [None, "Basic private-value", "Bearer bad-token", "Bearer " + "a" * 16385]
)
def test_authentication_precedes_query_validation(setup, path, authorization):
    headers = {} if authorization is None else {"Authorization": authorization}
    response = get(setup, path, "home_id=INVALID&subject_id=private-value", headers=headers)
    error(response, 401, "unauthenticated")
    assert "private-value" not in response.text


@pytest.mark.tc035_02
@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://wrong.example"},
        {"aud": "other-api"},
        {"aud": ["home-api"]},
        {"exp": 1},
        {"iat": int(time.time()) + 3600},
        {"nbf": int(time.time()) + 3600},
        {"sub": ""},
        {"sub": 1},
        {"family_member_id": None},
        {"role": []},
        {"realm_access": []},
        {"realm_access": {"roles": [1]}},
        {"exp": "9999999999"},
        {"iat": True},
        {"nbf": "1"},
    ],
)
def test_invalid_signed_claims(setup, signing_key, changes):
    response = get(setup, headers={"Authorization": "Bearer " + token(signing_key, **changes)})
    error(response, 401, "unauthenticated")


@pytest.mark.tc035_02
@pytest.mark.parametrize("missing", ["iss", "aud", "exp", "iat", "sub", "family_member_id"])
def test_missing_required_claim(setup, signing_key, missing):
    payload = claims()
    del payload[missing]
    encoded = jwt.encode(payload, signing_key, algorithm="RS256", headers={"kid": "test-key"})
    error(get(setup, headers={"Authorization": "Bearer " + encoded}), 401, "unauthenticated")


@pytest.mark.tc035_02
@pytest.mark.parametrize("kind", ["unknown-key", "wrong-signature", "hs256", "none", "critical"])
def test_signature_algorithm_and_key_boundary(setup, signing_key, kind):
    key = signing_key
    headers = {"kid": "test-key"}
    algorithm = "RS256"
    if kind == "unknown-key":
        headers["kid"] = "unknown"
    if kind == "wrong-signature":
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    if kind == "hs256":
        key, algorithm = b"fictional-test-secret-only-32bytes", "HS256"
    if kind == "none":
        key, algorithm = None, "none"
    if kind == "critical":
        headers["crit"] = ["unhandled"]
    encoded = jwt.encode(claims(), key, algorithm=algorithm, headers=headers)
    error(get(setup, headers={"Authorization": "Bearer " + encoded}), 401, "unauthenticated")


@pytest.mark.tc035_02
@pytest.mark.parametrize(
    "changes",
    [
        {"sub": "subject-denied"},
        {"family_member_id": "member-denied"},
        {"role": "admin"},
        {"role": "kid"},
        {"role": "unknown"},
        {"role": None},
        {"realm_access": {"roles": ["kid"]}},
    ],
)
@pytest.mark.parametrize("path", PATHS)
def test_exact_grant_and_role_isolation(setup, signing_key, changes, path):
    encoded = token(signing_key, **changes)
    error(get(setup, path, headers={"Authorization": "Bearer " + encoded}), 403, "forbidden")


@pytest.mark.tc035_02
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("home", ["home-other", "home-absent"])
def test_cross_home_denied_without_membership_disclosure(setup, path, home):
    error(get(setup, path, "home_id=" + home + "&now_ms=0"), 403, "forbidden")


@pytest.mark.tc035_02
@pytest.mark.parametrize("path", PATHS)
def test_authorization_before_bad_device_or_filter_diagnostics(setup, path):
    path = path.replace("device-one", "INVALID")
    error(get(setup, path, "home_id=home-other&area_id=INVALID"), 403, "forbidden")


@pytest.mark.tc035_02
@pytest.mark.parametrize(
    "changes",
    [
        {"sub": "subject-reader", "family_member_id": "member-reader"},
        {"sub": "subject-child", "family_member_id": "member-child", "role": "kid"},
        {"role": "go_getter"},
        {"role": None, "realm_access": {"roles": ["adult", "go_getter", "unrelated"]}},
    ],
)
@pytest.mark.parametrize("path", PATHS)
def test_valid_reader_child_and_gateway_aliases(setup, signing_key, changes, path):
    response = get(
        setup, path, headers={"Authorization": "Bearer " + token(signing_key, **changes)}
    )
    assert response.status_code == 200, response.text


@pytest.mark.tc035_02
def test_same_device_id_other_home_uses_own_exact_grant(setup, signing_key):
    headers = {"Authorization": "Bearer " + token(signing_key, sub="subject-other")}
    response = get(setup, "/api/devices/device-one", "home_id=home-other", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["device"]["home_id"] == "home-other"
    error(get(setup, headers=headers), 403, "forbidden")


@pytest.mark.tc035_02
def test_spoofed_headers_and_token_policy_do_not_grant(setup, signing_key):
    headers = {
        "Authorization": "Bearer "
        + token(
            signing_key,
            sub="subject-denied",
            home_id="home-example",
            allowed_homes=["home-example"],
        ),
        "X-Subject-Id": "subject-example",
        "X-Role": "adult",
        "X-Family-Member-Id": "member-example",
    }
    error(get(setup, headers=headers), 403, "forbidden")
    error(get(setup, headers={"X-Subject-Id": "subject-example"}), 401, "unauthenticated")


@pytest.mark.tc035_02
def test_duplicate_authorization_rejected(setup):
    value = setup["headers"]["Authorization"]
    error(
        get(setup, headers=[("Authorization", value), ("Authorization", value)]),
        401,
        "unauthenticated",
    )


@pytest.mark.tc035_03
@pytest.mark.parametrize(
    "path,query",
    [
        ("/api/devices/device-absent", "home_id=home-example"),
        ("/api/devices", "home_id=home-example&area_id=area-absent"),
    ],
)
def test_missing_is_distinct_from_empty(setup, path, query):
    response = get(setup, path, query)
    assert response.status_code == 404
    assert response.json() == {"status": "not_found", "data": None}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.tc035_03
def test_uninitialized_literal_state(setup):
    response = get(setup, "/api/devices/device-one")
    assert response.status_code == 200
    assert response.json()["data"]["state"] == {
        "status": "found",
        "revision": 0,
        "updated_at_ms": None,
        "freshness": "uninitialized",
        "state": {
            "home_id": "home-example",
            "device_id": "device-one",
            "desired_state": None,
            "reported_state": {},
            "availability": {"status": "unknown", "observed_at": None, "ordering": None},
        },
    }


@pytest.mark.tc035_03
@pytest.mark.parametrize("now,expected", [(100, "fresh"), (110, "fresh"), (111, "stale")])
@pytest.mark.parametrize("path", ["/api/twin/snapshot", "/api/devices/device-one"])
def test_freshness_offline_false_and_desired_state(setup, now, expected, path):
    value = state()
    value["desired_state"] = {"revision": 1, "values": {"is_on": True}, "report_baseline": None}
    setup["store"].put(
        context(),
        home_id="home-example",
        device_id="device-one",
        state=value,
        expected_revision=0,
        now_ms=100,
    )
    setup["clock"][0] = now
    response = get(setup, path)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    view = data["states"][0] if "states" in data else data["state"]
    assert view == {
        "status": "found",
        "state": value,
        "revision": 1,
        "updated_at_ms": 100,
        "freshness": expected,
    }
    assert view["state"]["reported_state"]["is_on"]["value"] is False
    assert view["state"]["desired_state"]["values"]["is_on"] is True


@pytest.mark.tc035_03
@pytest.mark.parametrize("bad", [99, -1, True, float("nan"), "private-clock"])
def test_clock_failures_are_unavailable(setup, bad):
    setup["store"].put(
        context(),
        home_id="home-example",
        device_id="device-one",
        state=state(),
        expected_revision=0,
        now_ms=100,
    )
    setup["clock"][0] = bad
    error(get(setup, "/api/twin/snapshot"), 503, "state_unavailable")


@pytest.mark.tc035_03
@pytest.mark.parametrize(
    "query",
    [
        "",
        "home_id=home-example&home_id=home-other",
        "home_id=home-example&area_id=area-main",
        "home_id=home-example&now_ms=0",
        "home_id=home-example&max_age_ms=999999",
        "home_id=home-example&role=admin",
        "home_id=home-example&family_member_id=member-reader",
        "home_id=home-example&subject_id=subject-reader",
    ],
)
def test_strict_query_contract(setup, query):
    error(get(setup, query=query), 400, "invalid_request")


@pytest.mark.tc035_03
@pytest.mark.parametrize(
    "path,query",
    [
        ("/api/devices/INVALID", "home_id=home-example"),
        ("/api/devices", "home_id=home-example&area_id=INVALID"),
        ("/api/devices", "home_id=home-example&area_id=area-main&area_id=area-empty"),
    ],
)
def test_invalid_selectors(setup, path, query):
    error(get(setup, path, query), 400, "invalid_request")


@pytest.mark.tc035_03
def test_get_body_and_write_method_rejected(setup):
    response = setup["client"].request(
        "GET", "/api/home?home_id=home-example", headers=setup["headers"], content=b"private-value"
    )
    error(response, 400, "invalid_request")
    response = setup["client"].post(
        "/api/devices?home_id=home-example", headers=setup["headers"], json={"action": "turn_on"}
    )
    error(response, 405, "method_not_allowed")


@pytest.mark.tc035_03
def test_unexpected_exception_is_fixed_and_redacted(setup, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("private-household-and-token")

    monkeypatch.setattr(HomeQueryService, "home", broken)
    response = get(setup)
    error(response, 500, "internal_error")
    assert "private-household-and-token" not in response.text


@pytest.mark.tc035_03
def test_verifier_failure_does_not_retain_token_chain(setup):
    with pytest.raises(AuthenticationError) as caught:
        setup["verifier"].verify("private-token")
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert str(caught.value) == "unauthenticated"
    assert "private" not in repr(setup["verifier"])


@pytest.mark.tc035_04
def test_openapi_matches_exact_routes_and_documents_security(setup):
    response = setup["client"].get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    expected = json.loads(Path(__file__).parents[1].joinpath("openapi.json").read_text())
    assert spec == expected
    assert set(spec["paths"]) == set(PATHS[:-1] + ["/api/devices/{device_id}"])
    for path, methods in spec["paths"].items():
        assert set(methods) == {"get"}
        op = methods["get"]
        assert op["security"] == [{"HTTPBearer": []}]
        assert "422" not in op["responses"]
        parameters = {p["name"]: p for p in op["parameters"]}
        assert parameters["home_id"]["required"] is True
        assert "now_ms" not in parameters
        assert set(op["responses"]) >= {"200", "400", "401", "403", "404", "500", "503"}
    assert "Fictional" not in json.dumps(spec)
    assert "StateView" in spec["components"]["schemas"]
    assert "freshness" in spec["components"]["schemas"]["StateView"]["properties"]
    for path in ["/home", "/areas", "/devices", "/state", "/api/tasks", "/api/events"]:
        error(setup["client"].get(path), 404, "not_found")


@pytest.mark.tc035_04
@pytest.mark.parametrize("value", [True, -1, 86400001, float("inf")])
def test_finite_freshness_config(setup, value):
    with pytest.raises(ValueError, match="invalid_api_configuration"):
        create_app(service=setup["service"], verifier=setup["verifier"], max_age_ms=value)


@pytest.mark.tc035_04
def test_explicit_composition_required(setup):
    with pytest.raises(TypeError):
        create_app()
    with pytest.raises(ValueError, match="invalid_api_configuration"):
        create_app(service=None, verifier=setup["verifier"])
    with pytest.raises(ValueError, match="invalid_auth_configuration"):
        TokenVerifier(issuer="https://idp.example", audience="home-api", public_keys={})
    with pytest.raises(ValueError, match="invalid_auth_configuration"):
        TokenVerifier(
            issuer="https://idp.example",
            audience="home-api",
            public_keys={"test-key": b"private-invalid-key"},
        )
    # App instances do not share a process-global identity/grant registry.
    other = create_app(service=setup["service"], verifier=setup["verifier"])
    assert TestClient(other).get("/api/home?home_id=home-example").status_code == 401
