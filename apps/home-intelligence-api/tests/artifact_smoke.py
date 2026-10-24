"""Standalone installed HTTP smoke; explicit checks remain active under python -O."""

import hashlib
import json
import sys
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from home_device_fabric.home_queries import HomeQueryService
from home_device_fabric.state_store import CurrentStateStore
from home_intelligence_api import TokenVerifier, create_app
from starlette.testclient import TestClient


def check():
    checks = 0

    def require(value):
        nonlocal checks
        checks += 1
        if not value:
            raise RuntimeError("installed_api_contract_failed")

    import home_device_fabric
    import home_intelligence_api
    import state_schema

    for module in (home_intelligence_api, home_device_fabric, state_schema):
        require(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()))
    inventory = {
        "schema_version": 1,
        "home": {"id": "home-example", "name": "Fictional", "residence_type": "apartment"},
        "areas": [],
        "floors": [],
        "area_groups": [],
        "labels": [],
        "devices": [
            {
                "id": "device-one",
                "home_id": "home-example",
                "name": "Fictional device",
                "area_id": None,
            }
        ],
    }
    context = {
        "subject_id": "subject-example",
        "family_member_id": "member-example",
        "home_id": "home-example",
        "role": "adult",
    }
    store = CurrentStateStore(inventories=[inventory], grants=[{**context, "access": "write"}])
    service = HomeQueryService(store=store, capabilities=[])
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    verifier = TokenVerifier(
        issuer="https://idp.example/realm", audience="home-api", public_keys={"smoke": public}
    )
    clock = [100]
    app = create_app(service=service, verifier=verifier, clock_ms=lambda: clock[0], max_age_ms=10)
    now = int(time.time())
    claims = {
        "iss": "https://idp.example/realm",
        "aud": "home-api",
        "iat": now - 1,
        "exp": now + 120,
        "sub": context["subject_id"],
        "family_member_id": context["family_member_id"],
        "role": "adult",
    }
    token = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "smoke"})
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + token}
    path = "/api/devices/device-one?home_id=home-example"
    require(client.get(path).status_code == 401)
    for route in [
        "/api/home",
        "/api/areas",
        "/api/devices",
        "/api/twin/snapshot",
        "/api/devices/device-one",
    ]:
        response = client.get(route + "?home_id=home-example", headers=headers)
        require(response.status_code == 200)
        require(response.headers["cache-control"] == "no-store")
    detail = client.get(path, headers=headers).json()["data"]
    require(detail["state"]["freshness"] == "uninitialized")
    require(detail["capabilities"] == {"status": "uninitialized", "data": None})
    require(
        client.get("/api/devices/absent?home_id=home-example", headers=headers).json()
        == {"status": "not_found", "data": None}
    )
    require(
        client.get("/api/devices/device-one?home_id=home-other", headers=headers).status_code == 403
    )
    require(client.get(path + "&now_ms=0", headers=headers).status_code == 400)
    require(client.get("/api/home?home_id=INVALID", headers=headers).status_code == 400)
    require(client.get("/api/home?home_id=INVALID").status_code == 401)
    invalid_device = "/api/devices/INVALID?home_id=home-example"
    require(client.get(invalid_device).status_code == 401)
    require(client.get(invalid_device, headers=headers).status_code == 400)
    list_token = jwt.encode(
        {**claims, "aud": ["other-api", "home-api"]},
        private, algorithm="RS256", headers={"kid": "smoke"},
    )
    require(client.get(path, headers={"Authorization": "Bearer " + list_token}).status_code == 200)
    require(client.post("/api/devices?home_id=home-example", headers=headers).status_code == 405)
    store.put(
        context,
        home_id="home-example",
        device_id="device-one",
        expected_revision=0,
        now_ms=100,
        state={
            "home_id": "home-example",
            "device_id": "device-one",
            "desired_state": None,
            "reported_state": {},
            "availability": {
                "status": "offline",
                "observed_at": "2026-10-23T00:00:00Z",
                "ordering": {"epoch": 1, "sequence": 1},
            },
        },
    )
    clock[0] = 111
    detail = client.get(path, headers=headers).json()["data"]
    require(detail["state"]["freshness"] == "stale")
    require(detail["state"]["state"]["availability"]["status"] == "offline")
    clock[0] = 99
    require(client.get(path, headers=headers).status_code == 503)
    spec = client.get("/openapi.json").json()
    require(
        set(spec["paths"])
        == {
            "/api/home",
            "/api/areas",
            "/api/devices",
            "/api/twin/snapshot",
            "/api/devices/{device_id}",
        }
    )
    require(all(op["get"]["security"] == [{"HTTPBearer": []}] for op in spec["paths"].values()))
    for route, methods in spec["paths"].items():
        require(("404" in methods["get"]["responses"]) == (route in (
            "/api/devices", "/api/devices/{device_id}"
        )))
    require(any(
        p["name"] == "device_id" and p["schema"].get("pattern") == "^[a-z][a-z0-9_-]{0,63}$"
        for p in spec["paths"]["/api/devices/{device_id}"]["get"]["parameters"]
    ))
    return {
        "checks": checks,
        "offline": True,
        "openapi_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
