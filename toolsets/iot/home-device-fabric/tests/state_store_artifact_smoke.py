"""Installed state-store checks; runtime imports stay lazy for collection gates."""

import json


def context(home="home-example", member="member-example", role="adult"):
    return {
        "subject_id": "subject-example",
        "family_member_id": member,
        "home_id": home,
        "role": role,
    }


def inventory(home="home-example"):
    return {
        "schema_version": 1,
        "home": {"id": home, "name": "Fictional", "residence_type": "apartment"},
        "floors": [],
        "areas": [],
        "labels": [],
        "area_groups": [],
        "devices": [
            {"id": device, "home_id": home, "name": "Fixture", "area_id": None, "labels": []}
            for device in ("device-one", "device-two")
        ],
    }


def configuration():
    return {
        "inventories": [inventory(), inventory("home-other")],
        "grants": [
            {**context(), "access": "write"},
            {**context(member="member-reader"), "access": "read"},
            {**context(member="member-child", role="kid"), "access": "read"},
            {**context("home-other"), "access": "write"},
        ],
    }


def snapshot(home="home-example", device="device-one", value=False):
    return {
        "home_id": home,
        "device_id": device,
        "desired_state": None,
        "reported_state": {
            "is_on": {
                "status": "known",
                "value": value,
                "observed_at": "2026-10-17T00:00:00Z",
                "ordering": {"epoch": 1, "sequence": 1},
            }
        },
        "availability": {
            "status": "online",
            "observed_at": "2026-10-17T00:00:00Z",
            "ordering": {"epoch": 1, "sequence": 1},
        },
    }


def check():
    from home_device_fabric.state_store import CurrentStateStore, StateNotFound, StateStoreError

    def require(value):
        if not value:
            raise RuntimeError("installed_state_store_check_failed")

    store = CurrentStateStore(**configuration())
    args = {"home_id": "home-example", "device_id": "device-one"}
    initial = store.read(context(), **args, now_ms=0, max_age_ms=0)
    require(initial.revision == 0 and initial.freshness == "uninitialized")
    saved = store.put(context(), **args, state=snapshot(), expected_revision=0, now_ms=100)
    require(
        saved.revision == 1 and saved.state.to_dict()["reported_state"]["is_on"]["value"] is False
    )
    require(store.read(context(), **args, now_ms=110, max_age_ms=10).freshness == "fresh")
    require(store.read(context(), **args, now_ms=111, max_age_ms=10).freshness == "stale")
    detached = saved.to_dict()
    detached["state"]["reported_state"].clear()
    require(bool(store.read(context(), **args, now_ms=100, max_age_ms=0).state.reported_state))
    require(
        isinstance(
            store.read(
                context(),
                home_id="home-example",
                device_id="missing-device",
                now_ms=100,
                max_age_ms=0,
            ),
            StateNotFound,
        )
    )
    for caller, code, expected in (
        (context(member="member-reader"), "forbidden", 1),
        (context(), "revision_conflict", 0),
    ):
        try:
            store.put(caller, **args, state=snapshot(), expected_revision=expected, now_ms=100)
        except StateStoreError as error:
            require(error.code == code)
        else:
            require(False)
    require(
        store.read(
            context("home-other"),
            home_id="home-other",
            device_id="device-one",
            now_ms=100,
            max_age_ms=0,
        ).revision
        == 0
    )
    restarted = CurrentStateStore(**configuration())
    rebuilt = restarted.rebuild(
        context(),
        home_id="home-example",
        now_ms=200,
        states={"schema_version": 1, "states": [snapshot(), snapshot(device="device-two")]},
    )
    require(len(rebuilt) == 2 and all(view.revision == 1 for view in rebuilt))
    require(restarted.read(context(), **args, now_ms=200, max_age_ms=0).freshness == "fresh")
    try:
        restarted.rebuild(
            context(),
            home_id="home-example",
            now_ms=201,
            states={"schema_version": 1, "states": [snapshot()]},
        )
    except StateStoreError as error:
        require(error.code == "incomplete_snapshot")
    else:
        require(False)
    return {"checks": 12, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
