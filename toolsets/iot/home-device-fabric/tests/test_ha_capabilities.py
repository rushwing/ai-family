"""REQ-033 proposed verification; literal fictional metadata, no live HA."""

import builtins
import copy
import importlib
import json
import math
import pickle
from pathlib import Path

import pytest


def runtime():
    return importlib.import_module("home_device_fabric.ha_capabilities")


def fixtures():
    mapper = importlib.import_module("home_device_fabric.ha_mapping")
    config = {
        "schema_version": 1,
        "home": {"id": "home-example", "name": "Example", "residence_type": "other"},
        "provider_instance_id": "ha-example", "area_ids": {},
        "device_ids": {"raw-device": "device-example"}, "entity_ids": {},
    }
    states = [
        {"entity_id": "switch.main", "state": "off", "attributes": {}},
        {"entity_id": "cover.main", "state": "open", "attributes": {
            "supported_features": 7, "current_position": 45}},
        {"entity_id": "sensor.temperature", "state": "20", "attributes": {
            "device_class": "temperature", "unit_of_measurement": "°C"}},
        {"entity_id": "sensor.humidity", "state": "35", "attributes": {
            "device_class": "humidity", "unit_of_measurement": "%"}},
        {"entity_id": "sensor.power", "state": "-12", "attributes": {
            "device_class": "power", "unit_of_measurement": "W"}},
        {"entity_id": "sensor.battery", "state": "0", "attributes": {
            "device_class": "battery", "unit_of_measurement": "%"}},
    ]
    data = {"devices": [{"id": "raw-device"}], "areas": [],
            "entities": [{"entity_id": row["entity_id"], "device_id": "raw-device"}
                         for row in states], "states": states}
    mapped = mapper.HARegistryMapper(config).map(data).for_adapter()
    return mapped, data


def infer(mapped=None, data=None, instance="ha-example"):
    if mapped is None or data is None:
        default_mapped, default_data = fixtures()
        mapped = default_mapped if mapped is None else mapped
        data = default_data if data is None else data
    return runtime().HACapabilityInferrer(provider_instance_id=instance).infer(
        inventory=mapped["inventory"], bindings=mapped["bindings"], discovery=data)


def capabilities(result):
    return result.for_adapter()["devices"][0]["capabilities"]


@pytest.mark.tc033_01
@pytest.mark.parametrize("identity,prop,entity,attribute", [
    ("home.switchable", "is_on", "switch.main", None),
    ("home.positionable", "position_percent", "cover.main", "current_position"),
    ("home.temperature_sensor", "temperature_c", "sensor.temperature", None),
    ("home.humidity_sensor", "relative_humidity_percent", "sensor.humidity", None),
    ("home.power_meter", "power_w", "sensor.power", None),
    ("home.battery_powered", "battery_percent", "sensor.battery", None),
])
def test_six_exact_descriptors_and_property_sources(identity, prop, entity, attribute):
    emitted = capabilities(infer())
    assert [row["descriptor"]["capability_id"] for row in emitted] == sorted(
        row["descriptor"]["capability_id"] for row in emitted)
    rows = {row["descriptor"]["capability_id"]: row for row in emitted}
    assert sorted(rows) == ["home.battery_powered", "home.humidity_sensor", "home.positionable",
                            "home.power_meter", "home.switchable", "home.temperature_sensor"]
    catalogue = importlib.import_module("state_schema.initial_capabilities")
    expected = catalogue.load_initial_capabilities().get(identity, 1).to_dict()
    assert rows[identity]["descriptor"] == expected
    mapping = rows[identity]["provider_mapping"]
    assert mapping["provider"] == "ha"
    assert mapping["provider_instance_id"] == "ha-example"
    assert mapping["entity_id"] == entity
    assert mapping["properties"] == {prop: {
        "source": "state" if attribute is None else "attribute", "attribute": attribute}}
    assert set(mapping["actions"]) == set(expected["actions"])


@pytest.mark.tc033_01
def test_literal_action_routes_and_schemas():
    rows = {row["descriptor"]["capability_id"]: row for row in capabilities(infer())}
    switch, cover = rows["home.switchable"], rows["home.positionable"]
    assert switch["provider_mapping"]["actions"] == {"set_on": {
        "domain": "switch", "selector": "is_on", "services": {
            "true": "turn_on", "false": "turn_off"}, "service_data": {}}}
    assert cover["provider_mapping"]["actions"] == {"set_position": {
        "domain": "cover", "service": "set_cover_position",
        "parameters": {"position": {"input": "position_percent"}}}}
    assert switch["descriptor"]["actions"]["set_on"]["input_schema"] == {
        "type": "object", "properties": {"is_on": {"type": "boolean"}},
        "required": ["is_on"], "additionalProperties": False}
    assert cover["descriptor"]["actions"]["set_position"]["input_schema"] == {
        "type": "object", "properties": {"position_percent": {
            "type": "integer", "minimum": 0, "maximum": 100}},
        "required": ["position_percent"], "additionalProperties": False}
    for row in (switch, cover):
        action = next(iter(row["descriptor"]["actions"].values()))
        assert action["risk"] == "medium"
        assert action["idempotency"] == "safe_repeat"
        assert action["completion_policy"]["kind"] == "state_converged"


@pytest.mark.tc033_01
@pytest.mark.parametrize("value", [True, False, {"is_on": 1}, {}, {"is_on": True, "extra": 1}])
def test_advertised_action_schema_rejects_wrong_payload(value):
    api = importlib.import_module("state_schema.capability")
    descriptor = next(row["descriptor"] for row in capabilities(infer())
                      if row["descriptor"]["capability_id"] == "home.switchable")
    with pytest.raises(api.CapabilityError):
        api.CapabilityDescriptor.from_dict(descriptor).validate_payload(
            "action_input", "set_on", value)


@pytest.mark.tc033_02
@pytest.mark.parametrize("features,supported", [
    (0, False), (1, False), (2, False), (3, False), (4, True), (7, True),
    (8, False), (128, False), (132, True), (2147483647, True),
    (-1, False), (2147483648, False), (True, False), (False, False),
    (4.0, False), ("4", False), (None, False), ([], False), ({}, False),
])
def test_cover_absolute_position_requires_exact_feature_bit(features, supported):
    mapped, data = fixtures()
    data["states"][1]["attributes"] = {"supported_features": features}
    identities = [row["descriptor"]["capability_id"] for row in capabilities(infer(mapped, data))]
    assert ("home.positionable" in identities) is supported


@pytest.mark.tc033_02
@pytest.mark.parametrize("device_class,unit", [
    ("temperature", "°F"), ("temperature", "K"), ("temperature", "C"),
    ("Temperature", "°C"), (None, "°C"), ([], "°C"), ({}, "°C"),
    ("temperature", None), ("temperature", []), ("temperature", {}),
    ("power", "kW"), ("energy", "W"), ("battery", "V"), ("humidity", "percent"),
    ("humidity", "% "), ("humidity ", "%"), ("pressure", "%"),
])
def test_unsupported_sensor_metadata_never_guessed(device_class, unit):
    mapped, data = fixtures()
    data["states"][2]["attributes"] = {"device_class": device_class, "unit_of_measurement": unit}
    result = infer(mapped, data)
    assert "home.temperature_sensor" not in [row["descriptor"]["capability_id"]
                                             for row in capabilities(result)]
    assert result.to_redacted_dict()["counts"]["unsupported_entities"] >= 1


@pytest.mark.tc033_02
@pytest.mark.parametrize("domain", ["light", "fan", "climate", "binary_sensor", "input_boolean",
                                       "Switch", "switchx", "switch", "switch."])
def test_unhandled_domains_and_malformed_entity_names(domain):
    mapped, data = fixtures()
    entity = domain if domain in ("switch", "switch.") else domain + ".main"
    data["entities"][0]["entity_id"] = entity
    data["states"][0]["entity_id"] = entity
    mapped["bindings"]["bindings"][0]["mapping"]["entity_ids"].remove("switch.main")
    mapped["bindings"]["bindings"][0]["mapping"]["entity_ids"].append(entity)
    assert "home.switchable" not in [row["descriptor"]["capability_id"]
                                     for row in capabilities(infer(mapped, data))]


@pytest.mark.tc033_02
@pytest.mark.parametrize("state", ["unknown", "unavailable", "0", "-99", "not-a-number"])
def test_metadata_describes_capability_without_claiming_observation(state):
    mapped, data = fixtures()
    for row in data["states"]:
        row["state"] = state
        row["attributes"]["private_note"] = "never-export-this-value"
    result = infer(mapped, data)
    assert len(capabilities(result)) == 6
    assert result.for_adapter() == infer().for_adapter()
    assert "never-export-this-value" not in json.dumps(result.for_adapter())


@pytest.mark.tc033_02
def test_missing_states_empty_devices_and_unbound_states():
    mapped, data = fixtures()
    data["states"] = [{"entity_id": "switch.ghost", "state": "on", "attributes": {}}]
    result = infer(mapped, data)
    assert result.for_adapter() == {"rules_version": 1, "devices": [{
        "home_id": "home-example", "device_id": "device-example", "capabilities": []}]}
    assert result.to_redacted_dict() == {"rules_version": 1, "counts": {
        "devices": 1, "capabilities": 0, "unsupported_entities": 6, "ambiguous_entities": 0}}


@pytest.mark.tc033_02
@pytest.mark.parametrize("index", range(6))
def test_duplicate_supported_kind_omitted_without_first_or_last_selection(index):
    mapped, data = fixtures()
    extra = copy.deepcopy(data["states"][index])
    extra["entity_id"] += "_second"
    data["states"].append(extra)
    data["entities"].append({"entity_id": extra["entity_id"], "device_id": "raw-device"})
    mapped["bindings"]["bindings"][0]["mapping"]["entity_ids"].append(extra["entity_id"])
    result = infer(mapped, data)
    assert len(capabilities(result)) == 5
    assert extra["entity_id"] not in json.dumps(result.for_adapter())
    assert data["states"][index]["entity_id"] not in json.dumps(result.for_adapter())
    assert result.to_redacted_dict()["counts"]["ambiguous_entities"] == 2
    for rows in data.values():
        rows.reverse()
    assert infer(mapped, data).for_adapter() == result.for_adapter()


@pytest.mark.tc033_02
def test_fresh_projection_reorder_removal_and_reappearance():
    mapped, data = fixtures()
    engine = runtime().HACapabilityInferrer(provider_instance_id="ha-example")
    args = {**mapped, "discovery": data}
    original = engine.infer(**args).for_adapter()
    for rows in data.values():
        rows.reverse()
    assert engine.infer(**args).for_adapter() == original
    removed = data["states"].pop()
    assert len(capabilities(engine.infer(**args))) == 5
    data["states"].append(removed)
    assert engine.infer(**args).for_adapter() == original


@pytest.mark.tc033_03
@pytest.mark.parametrize("instance", [
    None, True, 1, "", "HA", "ha example", "ha-example ", "x" * 65])
def test_strict_instance_configuration(instance):
    with pytest.raises(runtime().HACapabilityError) as caught:
        runtime().HACapabilityInferrer(provider_instance_id=instance)
    assert caught.value.code == "invalid_configuration"
    assert caught.value.__context__ is None and caught.value.__cause__ is None


@pytest.mark.tc033_03
def test_other_instances_have_no_capabilities():
    result = infer(instance="ha-other")
    assert capabilities(result) == []
    assert result.to_redacted_dict()["counts"]["unsupported_entities"] == 0


@pytest.mark.tc033_03
@pytest.mark.parametrize("change", ["missing_entity", "disabled_entity", "wrong_parent",
                                       "missing_parent", "disabled_parent", "duplicate_binding"])
def test_binding_registry_consistency(change):
    mapped, data = fixtures()
    if change == "missing_entity":
        data["entities"].pop()
    elif change == "disabled_entity":
        data["entities"][0]["disabled_by"] = "private-cause"
    elif change == "wrong_parent":
        data["entities"][0]["device_id"] = "private-other"
    elif change == "missing_parent":
        data["devices"] = []
    elif change == "disabled_parent":
        data["devices"][0]["disabled_by"] = "private-cause"
    else:
        device = copy.deepcopy(mapped["inventory"]["devices"][0])
        device["id"] = "device-second"
        mapped["inventory"]["devices"].append(device)
        binding = copy.deepcopy(mapped["bindings"]["bindings"][0])
        binding["device_id"] = "device-second"
        mapped["bindings"]["bindings"].append(binding)
    with pytest.raises(runtime().HACapabilityError) as caught:
        infer(mapped, data)
    assert caught.value.code == "invalid_bindings"
    assert caught.value.__context__ is None
    assert "private" not in repr(caught.value)


@pytest.mark.tc033_03
def test_standalone_binding_and_grouped_capabilities_are_not_crossed():
    mapped, data = fixtures()
    data["entities"][0].pop("device_id")
    with pytest.raises(runtime().HACapabilityError):
        infer(mapped, data)
    mapped["bindings"]["bindings"][0]["mapping"] = {
        "entity_ids": ["switch.main"], "device_registry_id": None}
    assert [row["descriptor"]["capability_id"] for row in capabilities(infer(mapped, data))
            ] == ["home.switchable"]


@pytest.mark.tc033_03
@pytest.mark.parametrize("part", ["inventory", "bindings", "discovery"])
@pytest.mark.parametrize("bad", [None, [], True, "private-value", {"private_key": "private-value"}])
def test_bad_boundary_objects_redacted(part, bad):
    mapped, data = fixtures()
    args = {**mapped, "discovery": data}
    args[part] = bad
    with pytest.raises(runtime().HACapabilityError) as caught:
        runtime().HACapabilityInferrer(provider_instance_id="ha-example").infer(**args)
    assert caught.value.code == "invalid_" + part
    assert caught.value.to_dict() == {"code": "invalid_" + part}
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert "private" not in str(caught.value) + repr(caught.value)


@pytest.mark.tc033_03
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, b"private", {1: 2}, "\ud800"])
def test_whole_discovery_including_unbound_rows_is_validated(bad):
    mapped, data = fixtures()
    data["states"].append({"entity_id": "sensor.unbound", "state": "1", "attributes": {"x": bad}})
    with pytest.raises(runtime().HACapabilityError) as caught:
        infer(mapped, data)
    assert caught.value.code == "invalid_discovery"


@pytest.mark.tc033_03
@pytest.mark.parametrize("kind", ["depth", "integer", "records", "bytes", "nodes"])
def test_bounded_inputs_fail_before_projection(kind):
    mapped, data = fixtures()
    if kind == "depth":
        value = {}
        for _ in range(34):
            value = {"x": value}
    elif kind == "integer":
        value = 1 << 4096
    elif kind == "bytes":
        value = "x" * (16 * 1024 * 1024 + 1)
    elif kind == "nodes":
        value = [None] * 200001
    else:
        data["areas"] = [{"area_id": "a" + str(i), "name": "Room"} for i in range(10001)]
        value = None
    data["states"][0]["attributes"]["extra"] = value
    with pytest.raises(runtime().HACapabilityError) as caught:
        infer(mapped, data)
    assert caught.value.code == "input_limit"


@pytest.mark.tc033_03
@pytest.mark.parametrize("cyclic", [False, True])
def test_container_aliases_and_cycles_rejected(cyclic):
    mapped, data = fixtures()
    value = {}
    if cyclic:
        value["x"] = value
    data["states"][0]["attributes"] = value
    data["states"][1]["attributes"] = value
    with pytest.raises(runtime().HACapabilityError) as caught:
        infer(mapped, data)
    assert caught.value.code == "invalid_discovery"


@pytest.mark.tc033_03
def test_reference_integrity_and_home_scope():
    mapped, data = fixtures()
    mapped["bindings"]["bindings"][0]["home_id"] = "home-other"
    with pytest.raises(runtime().HACapabilityError) as caught:
        infer(mapped, data)
    assert caught.value.code == "invalid_bindings"


@pytest.mark.tc033_03
def test_detached_immutable_private_results_and_offline_inference(monkeypatch):
    mapped, data = fixtures()
    engine = runtime().HACapabilityInferrer(provider_instance_id="ha-example")
    original = copy.deepcopy({**mapped, "discovery": data})
    expected = engine.infer(**original).for_adapter()
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("forbidden file access")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", denied)
        patch.setattr(Path, "open", denied)
        result = engine.infer(**original)
        assert result.for_adapter() == expected
    assert attempts == []
    assert original == {**mapped, "discovery": data}
    exported = result.for_adapter()
    exported["devices"].clear()
    data["states"].clear()
    assert result.for_adapter() == expected
    assert "switch.main" not in repr(engine) + repr(result) + json.dumps(result.to_redacted_dict())
    for value in (engine, result):
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                operation(value)
        with pytest.raises((AttributeError, TypeError)):
            value._payload = "private"
    with pytest.raises(AttributeError):
        engine.__init__(provider_instance_id="ha-other")
    with pytest.raises(AttributeError):
        result.__init__("{}", (0, 0, 0, 0))
    assert result.for_adapter() == expected


@pytest.mark.tc033_03
def test_public_error_is_finite_immutable_and_nonserializable():
    error = runtime().HACapabilityError("invalid_discovery")
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            operation(error)
    with pytest.raises(AttributeError):
        error._code = "invalid_bindings"
    with pytest.raises(AttributeError):
        del error._code
    with pytest.raises(AttributeError):
        error.__init__("invalid_bindings")
    with pytest.raises(ValueError):
        runtime().HACapabilityError("private-value")


@pytest.mark.tc033_03
@pytest.mark.parametrize("control", [KeyboardInterrupt, SystemExit, GeneratorExit])
def test_process_control_propagates(monkeypatch, control):
    engine = runtime().HACapabilityInferrer(provider_instance_id="ha-example")
    mapped, data = fixtures()

    def stop(*args):
        raise control()

    monkeypatch.setattr(runtime(), "_discovery", stop)
    with pytest.raises(control):
        engine.infer(**mapped, discovery=data)


@pytest.mark.tc033_02
@pytest.mark.parametrize("entity", ["switch.a.b", "switch.A", "switch.a b", "switch.é"])
def test_invalid_ha_service_targets_do_not_advertise_actions(entity):
    mapped, data = fixtures()
    data["entities"][0]["entity_id"] = entity
    data["states"][0]["entity_id"] = entity
    members = mapped["bindings"]["bindings"][0]["mapping"]["entity_ids"]
    members.remove("switch.main")
    members.append(entity)
    assert "home.switchable" not in [row["descriptor"]["capability_id"]
                                     for row in capabilities(infer(mapped, data))]


@pytest.mark.tc033_01
def test_same_capability_on_two_devices_has_independent_routes_and_sorted_results():
    mapped, data = fixtures()
    mapped["inventory"]["devices"].insert(0, {
        "id": "device-second", "home_id": "home-example", "name": "Second",
        "area_id": None, "labels": []})
    mapped["bindings"]["bindings"].insert(0, {
        "home_id": "home-example", "device_id": "device-second", "provider": "ha",
        "provider_instance_id": "ha-example", "mapping": {
            "entity_ids": ["switch.second"], "device_registry_id": None}})
    data["entities"].append({"entity_id": "switch.second"})
    data["states"].append({"entity_id": "switch.second", "state": "on", "attributes": {}})
    result = infer(mapped, data)
    rows = result.for_adapter()["devices"]
    assert [row["device_id"] for row in rows] == ["device-example", "device-second"]
    assert [row["provider_mapping"]["entity_id"] for row in rows[1]["capabilities"]
            ] == ["switch.second"]
    assert result.to_redacted_dict()["counts"]["capabilities"] == 7
    for rows in data.values():
        rows.reverse()
    mapped["inventory"]["devices"].reverse()
    mapped["bindings"]["bindings"].reverse()
    assert infer(mapped, data).for_adapter() == result.for_adapter()


@pytest.mark.tc033_03
def test_corrupt_catalogue_fails_construction_without_private_context(monkeypatch):
    def broken():
        raise ValueError("private resource details")

    monkeypatch.setattr(runtime(), "load_initial_capabilities", broken)
    with pytest.raises(runtime().HACapabilityError) as caught:
        runtime().HACapabilityInferrer(provider_instance_id="ha-example")
    assert caught.value.code == "invalid_configuration"
    assert caught.value.__context__ is None and "private" not in repr(caught.value)
