"""Standalone installed query checks; explicit checks survive python -O."""

import json


def context(home="home-example", member="member-example", role="adult"):
    return {
        "subject_id": "subject-example",
        "family_member_id": member,
        "home_id": home,
        "role": role,
    }


def configuration():
    def inventory(home):
        return {
            "schema_version": 1,
            "home": {"id": home, "name": "Fictional", "residence_type": "apartment"},
            "floors": [],
            "labels": [],
            "area_groups": [],
            "areas": [
                {
                    "id": area,
                    "home_id": home,
                    "name": area,
                    "area_type": "living_room",
                    "floor_id": None,
                }
                for area in ("area-empty", "area-main")
            ],
            "devices": [
                {
                    "id": device,
                    "home_id": home,
                    "name": device,
                    "area_id": "area-main" if device == "device-one" else None,
                }
                for device in ("device-two", "device-one")
            ],
        }

    return {
        "inventories": [inventory("home-example"), inventory("home-other")],
        "grants": [
            {**context(), "access": "write"},
            {**context(member="member-reader"), "access": "read"},
            {**context(member="member-child", role="kid"), "access": "read"},
            {**context("home-other"), "access": "write"},
        ],
    }


def check():
    from home_device_fabric.home_queries import HomeQueryError, HomeQueryService, QueryResult
    from home_device_fabric.state_store import CurrentStateStore
    from state_schema.initial_capabilities import load_initial_capabilities

    checks = 0

    def require(value):
        nonlocal checks
        checks += 1
        if not value:
            raise RuntimeError("installed_home_query_check_failed")

    config = configuration()
    store = CurrentStateStore(**config)
    descriptor = load_initial_capabilities().get("home.switchable", 1).to_dict()
    metadata = [
        {"home_id": "home-example", "device_id": "device-one", "capabilities": [descriptor]}
    ]
    service = HomeQueryService(store=store, capabilities=metadata)
    args = {"home_id": "home-example"}
    require(service.home(context(), **args).to_dict()["data"] == config["inventories"][0]["home"])
    require(
        [row["id"] for row in service.areas(context(), **args).to_dict()["data"]]
        == ["area-empty", "area-main"]
    )
    require(
        [row["id"] for row in service.devices(context(), **args).to_dict()["data"]]
        == ["device-one", "device-two"]
    )
    require(
        service.devices(context(), **args, area_id="area-empty").to_dict()
        == {"status": "found", "data": []}
    )
    require(service.devices(context(), **args, area_id="area-absent").status == "not_found")
    require(service.device(context(), **args, device_id="device-one").status == "found")
    require(service.device(context(), **args, device_id="device-absent").status == "not_found")
    require(
        service.state(context(), **args, device_id="device-one", now_ms=0, max_age_ms=0).to_dict()[
            "data"
        ]["freshness"]
        == "uninitialized"
    )
    require(
        service.state(context(), **args, device_id="device-absent", now_ms=0, max_age_ms=0).status
        == "not_found"
    )
    require(len(service.states(context(), **args, now_ms=0, max_age_ms=0).to_dict()["data"]) == 2)
    require(
        service.capabilities(context(), **args, device_id="device-one").to_dict()["data"]
        == [descriptor]
    )
    require(
        service.capabilities(context(), **args, device_id="device-two").status == "uninitialized"
    )
    metadata[0]["capabilities"].clear()
    result = service.capabilities(context(), **args, device_id="device-one")
    result.to_dict()["data"].clear()
    require(len(result.to_dict()["data"]) == 1)
    try:
        service.device(context(member="member-denied"), **args, device_id="device-one")
    except HomeQueryError as error:
        require(error.code == "forbidden" and error.__context__ is None)
    else:
        require(False)
    require(service.home(context(member="member-child", role="kid"), **args).status == "found")
    require(
        repr(service) == "HomeQueryService(<redacted>)"
        and repr(result) == "QueryResult(<redacted>)"
    )
    state = {
        "home_id": "home-example",
        "device_id": "device-one",
        "desired_state": None,
        "reported_state": {},
        "availability": {"status": "unknown", "observed_at": None, "ordering": None},
    }
    store.put(
        context(), **args, device_id="device-one", state=state, expected_revision=0, now_ms=100
    )
    require(
        service.state(
            context(), **args, device_id="device-one", now_ms=110, max_age_ms=10
        ).to_dict()["data"]["freshness"]
        == "fresh"
    )
    require(
        service.states(context(), **args, now_ms=111, max_age_ms=10).to_dict()["data"][0][
            "freshness"
        ]
        == "stale"
    )
    try:
        service.state(context(), **args, device_id="device-one", now_ms=99, max_age_ms=10)
    except HomeQueryError as error:
        require(error.code == "clock_regression" and error.__context__ is None)
    else:
        require(False)
    try:
        service.home(context(), home_id="home-other")
    except HomeQueryError as error:
        require(error.code == "forbidden")
    else:
        require(False)
    for invalid_data in (object(), float("nan")):
        try:
            QueryResult("found", invalid_data)
        except HomeQueryError as error:
            require(error.code == "invalid_configuration" and error.__context__ is None)
        else:
            require(False)
    return {"checks": checks, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
