"""Installed event integration checks; explicit assertions survive -O."""

import json
import runpy
from pathlib import Path

# Explicit sibling test fixtures remain available under isolated Python (-I).
_normalizer = runpy.run_path(str(Path(__file__).with_name("ha_normalization_artifact_smoke.py")))
_store = runpy.run_path(str(Path(__file__).with_name("state_store_artifact_smoke.py")))
event, fixture, context = _normalizer["event"], _normalizer["fixture"], _store["context"]


def check():
    from home_device_fabric.ha_normalization import HAEventNormalizer
    from home_device_fabric.state_store import CurrentStateStore, StateStoreError

    checks = 0

    def require(value):
        nonlocal checks
        if not value:
            raise RuntimeError("installed_state_events_check_failed")
        checks += 1

    config = fixture()
    store = CurrentStateStore(
        inventories=[config["inventory"]], grants=[{**context(), "access": "write"}]
    )
    normalizer = HAEventNormalizer(**config)
    args = {"home_id": "home-example", "device_id": "device-example"}

    def delta(raw, sequence, epoch=1):
        return normalizer.normalize(
            event(raw), ordering={"epoch": epoch, "sequence": sequence}
        ).to_dict()

    def apply(payload, now=100):
        return store.apply(context(), **args, event=payload, now_ms=now)

    def fails(code, fn):
        try:
            fn()
        except StateStoreError as caught:
            require(caught.code == code)
        else:
            require(False)

    fails("epoch_uninitialized", lambda: apply(delta("on", 1)))
    require(store.advance_epoch(context(), home_id="home-example", epoch=1) == 1)
    first = apply(delta("on", 1))
    require(
        first.revision == 1 and first.state.to_dict()["reported_state"]["is_on"]["value"] is True
    )
    initial = first.state.to_dict()
    initial["desired_state"] = {
        "revision": 1,
        "values": {"is_on": False},
        "report_baseline": {"epoch": 1, "sequence": 1},
    }
    store.put(context(), **args, state=initial, expected_revision=1, now_ms=100)
    off = apply(delta("off", 2), 110)
    require(
        off.revision == 3
        and off.state.to_dict()["reported_state"]["is_on"]["value"] is False
        and off.state.desired_state is not None
    )
    replay = apply(delta("off", 2), 120)
    require(replay.revision == 3 and replay.updated_at_ms == 110 and replay.freshness == "stale")
    stale = apply(delta("on", 1), 120)
    require(stale.to_dict() == replay.to_dict())
    fails("invalid_event", lambda: apply(delta("on", 2), 120))
    offline = apply(delta("unavailable", 3), 120)
    require(
        offline.revision == 4
        and offline.state.availability.status == "offline"
        and offline.state.reported_state == off.state.reported_state
        and offline.state.desired_state == off.state.desired_state
    )
    require(store.advance_epoch(context(), home_id="home-example", epoch=2) == 2)
    fails("epoch_mismatch", lambda: apply(delta("on", 999), 130))
    fails("epoch_mismatch", lambda: apply(delta("on", 1, epoch=3), 130))
    fails(
        "epoch_regression", lambda: store.advance_epoch(context(), home_id="home-example", epoch=1)
    )
    recovered = apply(delta("on", 0, epoch=2), 130)
    require(
        recovered.revision == 5
        and recovered.state.availability.status == "online"
        and recovered.state.desired_state == off.state.desired_state
    )
    unknown = apply(delta("unknown", 1, epoch=2), 140)
    report = unknown.state.to_dict()["reported_state"]["is_on"]
    require(report["status"] == "unknown" and report["value"] is None)
    fails(
        "forbidden",
        lambda: store.apply(context(member="member-other"), **args, event={}, now_ms=False),
    )
    fails("clock_regression", lambda: apply(delta("off", 2, epoch=2), 139))
    private = delta("on", 2, epoch=2)
    private["private-key"] = "private-value"
    fails("invalid_event", lambda: apply(private, 140))
    require(store.read(context(), **args, now_ms=140, max_age_ms=0).to_dict() == unknown.to_dict())
    return {"checks": checks, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
