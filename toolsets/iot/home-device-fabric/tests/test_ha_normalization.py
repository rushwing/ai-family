"""REQ-028 explicit adapter behavior against canonical public contracts."""

import copy
import importlib
import pickle

import pytest
from ha_normalization_artifact_smoke import check, event, fixture
from state_schema.canonical_state import DeviceState, StateError, apply_state_update


@pytest.fixture
def api():
    return importlib.import_module("home_device_fabric.ha_normalization")


def normalize(api, raw="off", attrs=None, kind="switch", sequence=2, epoch=1):
    return (
        api.HAEventNormalizer(**fixture(kind))
        .normalize(event(raw, attrs), ordering={"epoch": epoch, "sequence": sequence})
        .to_dict()
    )


@pytest.mark.tc028_01
def test_binding_identity_detachment_and_instance_isolation(api):
    config = fixture()
    other = copy.deepcopy(config["bindings"]["bindings"][0])
    other["provider_instance_id"] = "ha-other"
    other["device_id"] = "device-other"
    config["inventory"]["devices"].append(
        {**config["inventory"]["devices"][0], "id": "device-other"}
    )
    config["bindings"]["bindings"].append(other)
    before = copy.deepcopy(config)
    client = api.HAEventNormalizer(**config)
    assert config == before
    config["bindings"]["bindings"][0]["device_id"] = "device-other"
    config["profiles"][0]["kind"] = "curtain"
    result = client.normalize(event(), ordering={"epoch": 0, "sequence": 0})
    assert result.device_id == "device-example"
    assert result.home_id == "home-example"
    assert result.to_dict()["reported_state"]["is_on"]["value"] is False
    snapshot = result.to_dict()
    snapshot["reported_state"]["is_on"]["ordering"]["sequence"] = 99
    assert result.to_dict()["reported_state"]["is_on"]["ordering"]["sequence"] == 0


@pytest.mark.tc028_01
@pytest.mark.parametrize(
    "target,value,code",
    [
        ("provider_instance_id", True, "invalid_configuration"),
        ("provider_instance_id", "https://private.invalid", "invalid_configuration"),
        ("profiles", {}, "invalid_configuration"),
        ("profiles", [None], "malformed_object"),
        ("profiles", [{"entity_id": "opaque.fixture", "kind": []}], "unsupported_kind"),
        ("profiles", [{"entity_id": "opaque.fixture", "kind": "light"}], "unsupported_kind"),
        ("profiles", [{"entity_id": "unknown.fixture", "kind": "switch"}], "unbound_entity"),
        ("profiles", [{"entity_id": " opaque.fixture", "kind": "switch"}], "malformed_entity"),
        (
            "profiles",
            [{"entity_id": "opaque.fixture", "kind": "switch", "private": True}],
            "invalid_configuration",
        ),
        ("profiles", [], "missing_profile"),
        ("bindings", {"schema_version": True, "bindings": []}, "invalid_configuration"),
        ("inventory", {}, "invalid_configuration"),
    ],
)
def test_invalid_configuration(api, target, value, code):
    config = fixture()
    config[target] = value
    before = copy.deepcopy(config)
    with pytest.raises(api.HANormalizationError) as error:
        api.HAEventNormalizer(**config)
    assert error.value.code == code
    assert config == before


@pytest.mark.tc028_01
@pytest.mark.parametrize(
    "mutation,code",
    [
        ("duplicate", "duplicate_profile"),
        ("multi", "unsupported_multi_entity"),
        ("unknown_device", "invalid_configuration"),
        ("cross_home", "invalid_configuration"),
        ("collision", "invalid_configuration"),
    ],
)
def test_ambiguous_configuration(api, mutation, code):
    config = fixture()
    binding = config["bindings"]["bindings"][0]
    if mutation == "duplicate":
        config["profiles"] *= 2
    elif mutation == "multi":
        binding["mapping"]["entity_ids"].append("opaque.second")
    elif mutation == "unknown_device":
        binding["device_id"] = "device-missing"
    elif mutation == "cross_home":
        binding["home_id"] = "home-other"
    else:
        config["bindings"]["bindings"].append(copy.deepcopy(binding))
    with pytest.raises(api.HANormalizationError) as error:
        api.HAEventNormalizer(**config)
    assert error.value.code == code


@pytest.mark.tc028_01
def test_empty_selected_instance_has_no_fallback(api):
    config = fixture()
    config["provider_instance_id"] = "ha-other"
    config["profiles"] = []
    client = api.HAEventNormalizer(**config)
    with pytest.raises(api.HANormalizationError, match="unbound_entity"):
        client.normalize(event(), ordering={"epoch": 1, "sequence": 1})


@pytest.mark.tc028_02
@pytest.mark.parametrize(
    "kind,raw,attrs,member,value",
    [
        ("switch", "on", {}, "is_on", True),
        ("switch", "off", {}, "is_on", False),
        ("curtain", "closed", {"current_position": 0}, "position_percent", 0),
        ("curtain", "open", {"current_position": 100}, "position_percent", 100),
        ("curtain", "opening", {"current_position": 43}, "position_percent", 43),
        ("curtain", "closing", {"current_position": 19}, "position_percent", 19),
        ("temperature", "0", {"unit_of_measurement": "°C"}, "temperature_c", 0.0),
        ("temperature", "-12.5", {"unit_of_measurement": "°C"}, "temperature_c", -12.5),
        ("temperature", "-273.15", {"unit_of_measurement": "°C"}, "temperature_c", -273.15),
        ("temperature", "+2.3e1", {"unit_of_measurement": "°C"}, "temperature_c", 23.0),
    ],
)
def test_known_values(api, kind, raw, attrs, member, value):
    result = normalize(api, raw, attrs, kind, sequence=0, epoch=0)
    report = result["reported_state"][member]
    assert report == {
        "status": "known",
        "value": value,
        "observed_at": "2026-10-17T00:30:00Z",
        "ordering": {"epoch": 0, "sequence": 0},
    }
    assert type(report["value"]) is type(value)
    assert result["availability"]["status"] == "online"
    assert DeviceState.from_dict(result).to_dict() == result


@pytest.mark.tc028_02
@pytest.mark.parametrize(
    "kind,raw,attrs,code",
    [
        ("switch", "ON", {}, "unsupported_state"),
        ("switch", "false", {}, "unsupported_state"),
        ("switch", False, {}, "malformed_state"),
        ("curtain", "stopped", {"current_position": 30}, "unsupported_state"),
        ("curtain", "open", {"current_position": True}, "invalid_position"),
        ("curtain", "open", {"current_position": 0.0}, "invalid_position"),
        ("curtain", "open", {"current_position": "50"}, "invalid_position"),
        ("curtain", "open", {"current_position": None}, "invalid_position"),
        ("curtain", "open", {"current_position": -1}, "invalid_position"),
        ("curtain", "open", {"current_position": 101}, "invalid_position"),
        ("temperature", "20", {}, "unsupported_unit"),
        ("temperature", "20", {"unit_of_measurement": "°F"}, "unsupported_unit"),
        ("temperature", "nan", {"unit_of_measurement": "°C"}, "invalid_temperature"),
        ("temperature", "-273.16", {"unit_of_measurement": "°C"}, "invalid_temperature"),
        ("temperature", "1e9999", {"unit_of_measurement": "°C"}, "invalid_temperature"),
        ("temperature", " 20", {"unit_of_measurement": "°C"}, "invalid_temperature"),
        ("temperature", "1_0", {"unit_of_measurement": "°C"}, "invalid_temperature"),
        ("temperature", "", {"unit_of_measurement": "°C"}, "invalid_temperature"),
    ],
)
def test_invalid_values(api, kind, raw, attrs, code):
    with pytest.raises(api.HANormalizationError) as error:
        normalize(api, raw, attrs, kind)
    assert error.value.code == code


@pytest.mark.tc028_02
@pytest.mark.parametrize(
    "stamp",
    [
        None,
        True,
        "2026-10-17T00:00:00",
        "2026-02-30T00:00:00Z",
        "2026-10-17T24:00:00Z",
        "2026-10-17T00:60:00Z",
        "2026-10-17T00:00:60Z",
        "2026-10-17T00:00:00+24:00",
        "2026-10-17T00:00:00+00:60",
        "2026-10-17T00:00:00.1234567Z",
        "0001-01-01T00:00:00+01:00",
    ],
)
def test_bad_timestamps(api, stamp):
    payload = event()
    payload["time_fired"] = stamp
    with pytest.raises(api.HANormalizationError, match="malformed_timestamp"):
        api.HAEventNormalizer(**fixture()).normalize(payload, ordering={"epoch": 1, "sequence": 1})


@pytest.mark.tc028_02
@pytest.mark.parametrize(
    "stamp,expected",
    [
        ("2026-10-17T00:00:00Z", "2026-10-17T00:00:00Z"),
        ("2026-10-17T00:00:00.123Z", "2026-10-17T00:00:00.123000Z"),
        ("2026-10-17T00:30:00-01:00", "2026-10-17T01:30:00Z"),
    ],
)
def test_timestamp_conversion(api, stamp, expected):
    payload = event()
    payload["time_fired"] = stamp
    result = (
        api.HAEventNormalizer(**fixture())
        .normalize(payload, ordering={"epoch": 1, "sequence": 1})
        .to_dict()
    )
    assert result["availability"]["observed_at"] == expected


@pytest.mark.tc028_02
@pytest.mark.parametrize(
    "ordering",
    [
        None,
        {},
        {"epoch": True, "sequence": 0},
        {"epoch": 0, "sequence": -1},
        {"epoch": 0, "sequence": 1.0},
        {"epoch": 0, "sequence": 1, "private": 1},
    ],
)
def test_invalid_ordering(api, ordering):
    with pytest.raises(api.HANormalizationError, match="invalid_ordering"):
        api.HAEventNormalizer(**fixture()).normalize(event(), ordering=ordering)


@pytest.mark.tc028_02
@pytest.mark.parametrize(
    "field,value,code",
    [
        ("event_type", "call_service", "wrong_event_type"),
        ("data", None, "malformed_object"),
        ("entity_id", "unknown.fixture", "unbound_entity"),
        ("entity_id", "", "malformed_entity"),
        ("old_state", False, "malformed_state"),
        ("new_state", [], "malformed_state"),
        ("attributes", None, "malformed_object"),
        ("nested_entity", "private.other", "identity_mismatch"),
    ],
)
def test_invalid_event(api, field, value, code):
    payload = event()
    if field in ("event_type", "data"):
        payload[field] = value
    elif field == "attributes":
        payload["data"]["new_state"][field] = value
    elif field == "nested_entity":
        payload["data"]["new_state"]["entity_id"] = value
    else:
        payload["data"][field] = value
    before = copy.deepcopy(payload)
    with pytest.raises(api.HANormalizationError) as error:
        api.HAEventNormalizer(**fixture()).normalize(payload, ordering={"epoch": 1, "sequence": 1})
    assert error.value.code == code
    assert payload == before


@pytest.mark.tc028_02
@pytest.mark.parametrize("field", ["old_state", "new_state"])
def test_missing_state_is_not_removal(api, field):
    payload = event()
    del payload["data"][field]
    with pytest.raises(api.HANormalizationError, match="malformed_state"):
        api.HAEventNormalizer(**fixture()).normalize(payload, ordering={"epoch": 1, "sequence": 1})


def apply(current, delta, epoch=1):
    return apply_state_update(
        current,
        current_epoch=epoch,
        reported_state=delta["reported_state"],
        availability=delta["availability"],
    )


@pytest.mark.tc028_03
@pytest.mark.parametrize("raw", ["unavailable", None, "unknown"])
def test_availability_intent_and_history(api, raw):
    current = normalize(api)
    current["desired_state"] = {
        "revision": 1,
        "values": {"is_on": True},
        "report_baseline": {"epoch": 1, "sequence": 1},
    }
    payload = event(raw)
    if raw is None:
        payload["data"]["new_state"] = None
    delta = (
        api.HAEventNormalizer(**fixture())
        .normalize(payload, ordering={"epoch": 1, "sequence": 3})
        .to_dict()
    )
    after = apply(current, delta)
    assert after["desired_state"] == current["desired_state"]
    if raw == "unknown":
        assert after["reported_state"]["is_on"]["status"] == "unknown"
        assert after["reported_state"]["is_on"]["value"] is None
        assert after["availability"]["status"] == "unknown"
    else:
        assert delta["reported_state"] == {}
        assert after["reported_state"] == current["reported_state"]
        assert after["availability"]["status"] == "offline"


@pytest.mark.tc028_03
def test_missing_position_is_unknown_not_inferred_endpoint(api):
    for raw in ("closed", "open"):
        delta = normalize(api, raw, {}, "curtain")
        assert delta["reported_state"]["position_percent"]["status"] == "unknown"
        assert delta["reported_state"]["position_percent"]["value"] is None
        assert delta["availability"]["status"] == "online"


@pytest.mark.tc028_03
def test_replay_stale_conflict_and_epoch_fencing(api):
    current = normalize(api, "on", sequence=5)
    assert apply(current, current) == current
    assert apply(current, normalize(api, "off", sequence=4)) == current
    assert apply(current, normalize(api, "unknown", sequence=4)) == current
    with pytest.raises(StateError):
        apply(current, normalize(api, "off", sequence=5))
    next_epoch = normalize(api, "off", epoch=2, sequence=0)
    assert apply(current, next_epoch, epoch=2) == next_epoch
    with pytest.raises(StateError):
        apply(next_epoch, current, epoch=2)
    with pytest.raises(StateError):
        apply(current, next_epoch, epoch=1)


@pytest.mark.tc028_03
def test_timestamp_reversal_does_not_reverse_order(api):
    current = normalize(api, "on", sequence=5)
    payload = event("off")
    payload["time_fired"] = "2000-01-01T00:00:00Z"
    delta = (
        api.HAEventNormalizer(**fixture())
        .normalize(payload, ordering={"epoch": 1, "sequence": 6})
        .to_dict()
    )
    assert apply(current, delta)["reported_state"]["is_on"]["value"] is False
    assert apply(delta, current) == delta


@pytest.mark.tc028_04
def test_privacy_repr_error_and_serialization(api):
    client = api.HAEventNormalizer(**fixture())
    payload = event()
    payload["private-key"] = "secret-payload"
    payload["context"] = {"user_id": "private-user"}
    payload["data"]["old_state"] = {"private-history": "secret-payload"}
    payload["data"]["new_state"]["attributes"]["private-key"] = "secret-payload"
    result = client.normalize(payload, ordering={"epoch": 1, "sequence": 1})
    public = repr(client) + repr(result) + repr(result.to_dict())
    for private in (
        "opaque.fixture",
        "ha-example",
        "secret-payload",
        "private-user",
        "private-key",
    ):
        assert private not in public
    with pytest.raises(TypeError, match="normalizer_serialization_forbidden"):
        pickle.dumps(client)
    config = fixture()
    config["bindings"]["bindings"][0]["mapping"]["secret-private-key"] = "secret-payload"
    with pytest.raises(api.HANormalizationError) as error:
        api.HAEventNormalizer(**config)
    assert error.value.__suppress_context__
    assert str(error.value) == "invalid_configuration: bindings"
    assert error.value.path == ("bindings",)


@pytest.mark.tc028_04
def test_offline_installed_smoke():
    assert check() == {"checks": 5, "offline": True}


@pytest.mark.tc028_02
@pytest.mark.ha_websocket_async
def test_subscription_delivery_composes_with_normalizer(api, monkeypatch):
    import asyncio
    import json

    from home_device_fabric.ha_subscription import HAStateSubscriptionClient
    from test_ha_subscription import ACK, AUTH, wait_for
    from test_ha_websocket import Socket, configuration, fake

    async def scenario():
        normalizer = api.HAEventNormalizer(**fixture())
        wire = json.dumps({"id": 1, "type": "event", "event": event()})
        socket = Socket([*AUTH, ACK, wire])
        fake(monkeypatch, [socket])
        delivered = []

        async def consume(payload):
            delivered.append(normalizer.normalize(payload, ordering={"epoch": 1, "sequence": 1}))

        client = HAStateSubscriptionClient(configuration(), consume)
        running = asyncio.create_task(client.run())
        try:
            await wait_for(lambda: len(delivered) == 1)
            assert delivered[0].to_dict()["reported_state"]["is_on"]["value"] is False
            assert client.subscription_health().subscribed
        finally:
            await client.aclose()
            await asyncio.wait_for(running, 3)
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]

    asyncio.run(scenario())
