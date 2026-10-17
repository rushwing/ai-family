"""Installed-package offline smoke; explicit checks survive optimized Python."""

import json


def fixture(kind="switch"):
    return {
        "inventory": {
            "schema_version": 1,
            "home": {"id": "home-example", "name": "Fictional", "residence_type": "apartment"},
            "floors": [], "areas": [], "labels": [], "area_groups": [],
            "devices": [{"id": "device-example", "home_id": "home-example", "name": "Fixture",
                         "area_id": None, "labels": []}],
        },
        "bindings": {"schema_version": 1, "bindings": [{
            "home_id": "home-example", "device_id": "device-example", "provider": "ha",
            "provider_instance_id": "ha-example", "mapping": {"entity_ids": ["opaque.fixture"]},
        }]},
        "provider_instance_id": "ha-example",
        "profiles": [{"entity_id": "opaque.fixture", "kind": kind}],
    }


def event(state="off", attributes=None):
    return {
        "event_type": "state_changed", "time_fired": "2026-10-17T01:30:00+01:00",
        "data": {"entity_id": "opaque.fixture", "old_state": None, "new_state": {
            "entity_id": "opaque.fixture", "state": state,
            "attributes": {} if attributes is None else attributes,
        }},
    }


def check():
    from unittest.mock import patch

    from home_device_fabric.ha_normalization import HAEventNormalizer, HANormalizationError
    from state_schema.canonical_state import DeviceState, StateError, apply_state_update

    normalizer = HAEventNormalizer(**fixture())
    delta = normalizer.normalize(event(), ordering={"epoch": 1, "sequence": 2}).to_dict()
    if (delta["reported_state"]["is_on"]["value"] is not False
            or delta["reported_state"]["is_on"]["observed_at"] != "2026-10-17T00:30:00Z"
            or delta["device_id"] != "device-example"):
        raise RuntimeError("installed_normalization_check_failed")
    offline = normalizer.normalize(event("unavailable"),
                                   ordering={"epoch": 1, "sequence": 3}).to_dict()
    retained = apply_state_update(delta, current_epoch=1,
                                  reported_state=offline["reported_state"],
                                  availability=offline["availability"])
    if (retained["reported_state"] != delta["reported_state"]
            or retained["availability"]["status"] != "offline"):
        raise RuntimeError("installed_normalization_check_failed")
    for kind, raw, attrs, member in (
        ("curtain", "closed", {"current_position": 0}, "position_percent"),
        ("temperature", "0", {"unit_of_measurement": "°C"}, "temperature_c"),
    ):
        value = HAEventNormalizer(**fixture(kind)).normalize(
            event(raw, attrs), ordering={"epoch": 1, "sequence": 1}).to_dict()
        if value["reported_state"][member]["value"] != 0:
            raise RuntimeError("installed_normalization_check_failed")
    try:
        normalizer.normalize(event("private-invalid"), ordering={"epoch": 1, "sequence": 1})
    except HANormalizationError as error:
        if error.code != "unsupported_state" or "private" in str(error):
            raise RuntimeError("installed_normalization_check_failed") from None
    else:
        raise RuntimeError("installed_normalization_check_failed")
    for raw in ("unknown", "unavailable"):
        payload = event(raw)
        del payload["data"]["new_state"]["attributes"]
        try:
            normalizer.normalize(payload, ordering={"epoch": 1, "sequence": 1})
        except HANormalizationError as error:
            if (error.code != "malformed_object"
                    or error.path != ("event", "data", "new_state", "attributes")):
                raise RuntimeError("installed_normalization_check_failed") from None
        else:
            raise RuntimeError("installed_normalization_check_failed")
    for offset, expected in (("+23:59", "2026-10-16T00:01:00Z"),
                             ("-23:59", "2026-10-17T23:59:00Z")):
        payload = event()
        payload["time_fired"] = "2026-10-17T00:00:00" + offset
        result = normalizer.normalize(payload, ordering={"epoch": 1, "sequence": 1}).to_dict()
        if result["availability"]["observed_at"] != expected:
            raise RuntimeError("installed_normalization_check_failed")
    with patch.object(DeviceState, "from_dict",
                      side_effect=StateError(("private-key",), "private-detail")):
        try:
            normalizer.normalize(event(), ordering={"epoch": 1, "sequence": 1})
        except HANormalizationError as error:
            if (str(error) != "invalid_observation: observation"
                    or error.__cause__ is not None or not error.__suppress_context__):
                raise RuntimeError("installed_normalization_check_failed") from None
        else:
            raise RuntimeError("installed_normalization_check_failed")
    return {"checks": 8, "offline": True}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
