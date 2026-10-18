"""Offline installed monotonic apply checks; explicit checks survive optimization."""

import json
import runpy
from pathlib import Path

# Load only explicit test fixtures; runtime imports resolve from installed packages.
_fixtures = runpy.run_path(str(Path(__file__).with_name("state_store_artifact_smoke.py")))
configuration, context, snapshot = (_fixtures[name] for name in (
    "configuration", "context", "snapshot"))


def event(*, epoch=1, sequence=1, value=False, status="online", device="device-one"):
    data = snapshot(device=device, value=value)
    order = {"epoch": epoch, "sequence": sequence}
    data["availability"]["ordering"] = order.copy()
    data["availability"]["status"] = status
    data["reported_state"]["is_on"]["ordering"] = order.copy()
    if status == "offline":
        data["reported_state"] = {}
    return data


def check():
    from home_device_fabric.state_store import CurrentStateStore, StateStoreError

    checks = 0

    def require(value):
        nonlocal checks
        checks += 1
        if not value:
            raise RuntimeError("installed_state_application_check_failed")

    store = CurrentStateStore(**configuration())
    args = {"home_id": "home-example", "device_id": "device-one"}

    def apply(data, now=100):
        return store.apply(context(), **args, event=data, now_ms=now)

    try:
        apply(event())
    except StateStoreError as error:
        require(error.code == "epoch_uninitialized")
    else:
        require(False)
    require(store.advance_epoch(context(), home_id="home-example", epoch=1) == 1)
    first = apply(event())
    require(first.revision == 1 and dict(first.state.reported_state)["is_on"].value is False)
    require(apply(event(), 101).revision == 1)
    require(apply(event(), 101).updated_at_ms == 100)
    require(apply(event(), 101).freshness == "stale")
    saved = snapshot()
    saved["desired_state"] = {
        "revision": 1, "values": {"is_on": True},
        "report_baseline": {"epoch": 1, "sequence": 1},
    }
    store.put(context(), **args, state=saved, expected_revision=1, now_ms=101)
    offline = apply(event(sequence=2, status="offline"), 102)
    require(offline.revision == 3 and offline.state.availability.status == "offline")
    require(offline.state.desired_state.to_dict() == saved["desired_state"])
    require(dict(offline.state.reported_state)["is_on"].value is False)
    recovered = apply(event(sequence=3, value=True), 103)
    require(recovered.revision == 4 and recovered.state.availability.status == "online")
    require(dict(recovered.state.reported_state)["is_on"].value is True)
    try:
        apply(event(sequence=3, value=False), 104)
    except StateStoreError as error:
        require(error.code == "invalid_event" and error.__context__ is None)
    else:
        require(False)
    store.advance_epoch(context(), home_id="home-example", epoch=2)
    require(store.read(context(), **args, now_ms=104, max_age_ms=0).revision == 4)
    try:
        apply(event(sequence=4), 104)
    except StateStoreError as error:
        require(error.code == "epoch_mismatch")
    else:
        require(False)
    require(apply(event(epoch=2, value=0), 104).revision == 5)
    require(store.read(context(), **args, now_ms=104, max_age_ms=0).updated_at_ms == 104)
    try:
        store.apply(context(member="member-reader"), **args, event={}, now_ms=105)
    except StateStoreError as error:
        require(error.code == "forbidden")
    else:
        require(False)
    detached = recovered.to_dict()
    detached["state"]["reported_state"].clear()
    require(bool(store.read(context(), **args, now_ms=104, max_age_ms=0).state.reported_state))
    return {"checks": checks, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
