"""Installed REQ-036 checks, explicit under -I and -O; no checkout imports."""
import json


def check():
    from home_device_fabric.ha_discovery import HADiscoveryError, HADiscoverySnapshot
    from home_device_fabric.ha_mapping import HARegistryMapper
    from home_device_fabric.reconciliation import ReconnectReconciler
    from home_device_fabric.state_store import CurrentStateStore
    from state_schema.canonical_state import StateCollection

    checks = 0

    def require(value):
        nonlocal checks
        if not value:
            raise RuntimeError("installed_reconciliation_check_failed")
        checks += 1

    caller = {"subject_id": "subject-example", "family_member_id": "member-example",
              "home_id": "home-example", "role": "adult"}
    home = {"id": "home-example", "name": "Fixture", "residence_type": "other"}
    inventory = {"schema_version": 1, "home": home, "floors": [], "areas": [],
                 "labels": [], "area_groups": [], "devices": [{"id": "device-one",
                 "home_id": home["id"], "name": "Fixture", "area_id": None, "labels": []}]}
    store = CurrentStateStore(inventories=[inventory], grants=[{**caller, "access": "write"}])
    args = {"home_id": home["id"], "device_id": "device-one", "now_ms": 100, "max_age_ms": 100}
    data = {"devices": [], "entities": [{"entity_id": "switch.example"}], "areas": [],
            "states": [{"entity_id": "switch.example", "state": "on", "attributes": {},
                        "last_updated": "2026-10-30T10:00:00Z"}]}
    labels = ("devices", "entities", "areas", "states")
    discovery = HADiscoverySnapshot(tuple(json.dumps(data[k]) for k in labels),
                                   tuple(len(data[k]) for k in labels))
    mapped = HARegistryMapper({"schema_version": 1, "home": home,
        "provider_instance_id": "ha-example", "area_ids": {}, "device_ids": {},
        "entity_ids": {"switch.example": "device-one"}}).map(data)
    reconciler = ReconnectReconciler(store=store, write_context=caller,
        registered_inventory=inventory, provider_instance_id="ha-example",
        profiles=[{"entity_id": "switch.example", "kind": "switch"}],
        max_buffer_events=10, max_input_bytes=100000)
    captured = []
    for i, time in enumerate(("09:59", "10:00", "10:01"), start=1):
        stamp = "2026-10-30T" + time + ":00Z"
        order = {"epoch": 1, "sequence": i}
        captured.append({"source_entity_id": "switch.example", "capture_ordinal": i,
            "observed_at": stamp, "original_ordering": order, "normalized_delta": {
                "home_id": home["id"], "device_id": "device-one", "desired_state": None,
                "reported_state": {"is_on": {"status": "known", "value": False,
                    "observed_at": stamp, "ordering": order}}, "availability": {
                    "status": "online", "observed_at": stamp, "ordering": order}}})

    def attempt(epoch, **changes):
        return reconciler.reconcile(**{"home_id": home["id"], "epoch": epoch,
            "attempt_number": 1, "max_attempts": 2, "discovery_result": discovery,
            "mapping_result": mapped, "buffered_events": captured,
            "current_states": StateCollection(1, (store.read(caller, **args).state,)),
            "now_ms": 100, **changes})

    require(attempt(2).outcome == "reconciled")
    row = store.read(caller, **args)
    require(dict(row.state.reported_state)["is_on"].value is False)
    require(row.state.availability.ordering.sequence == 1)
    require(row.revision == 1 and row.freshness == "fresh")
    failed = attempt(3, discovery_result=HADiscoveryError("timeout"), mapping_result=None)
    require(failed.outcome == "retryable_failure" and failed.state_stale)
    require(store.read(caller, **args).revision == 1)
    require(store.read(caller, **args).freshness == "stale")
    require(attempt(4, buffered_events=[]).outcome == "reconciled")
    require(dict(store.read(caller, **args).state.reported_state)["is_on"].value is True)
    require(store.read(caller, **args).revision == 2)
    require(attempt(4).failure_code == "epoch_conflict")
    require(store.read(caller, **args).revision == 2)
    require("switch.example" not in repr(reconciler))
    return {"checks": checks, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
