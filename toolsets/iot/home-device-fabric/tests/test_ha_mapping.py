"""REQ-032 proposed adversarial verification; fictional registry fixtures only."""

import copy
import json
import math
import pickle

import pytest
from home_device_fabric.ha_mapping import HAMappingError, HARegistryMapper
from state_schema.home_inventory import Inventory
from state_schema.provider_binding import BindingCollection


def configuration():
    return {
        "schema_version": 1,
        "home": {"id": "home-example", "name": "Example", "residence_type": "other"},
        "provider_instance_id": "ha-example",
        "area_ids": {"raw-room": "area-example"},
        "device_ids": {"raw-device": "device-example"},
        "entity_ids": {"sensor.solo": "device-solo"},
    }


def discovery():
    return {
        "areas": [{"area_id": "raw-room", "name": "Example room"}],
        "devices": [{"id": "raw-device", "name": "Example device", "area_id": "raw-room"}],
        "entities": [
            {"entity_id": "switch.example", "device_id": "raw-device"},
            {"entity_id": "sensor.example", "device_id": "raw-device"},
            {
                "entity_id": "sensor.solo",
                "device_id": None,
                "area_id": "raw-room",
                "original_name": "Example standalone",
            },
        ],
        "states": [{"entity_id": "switch.example", "state": "off", "attributes": {}}],
    }


def project(data=None, config=None):
    return HARegistryMapper(configuration() if config is None else config).map(
        discovery() if data is None else data
    )


@pytest.mark.tc032_01
def test_literal_projection_and_shared_validation():
    result = project()
    value = result.for_adapter()
    assert value["inventory"] == {
        "schema_version": 1,
        "home": {"id": "home-example", "name": "Example", "residence_type": "other"},
        "floors": [],
        "labels": [],
        "area_groups": [],
        "areas": [
            {
                "id": "area-example",
                "home_id": "home-example",
                "name": "Example room",
                "area_type": "other",
                "floor_id": None,
                "labels": [],
                "aliases": [],
            }
        ],
        "devices": [
            {
                "id": "device-example",
                "home_id": "home-example",
                "name": "Example device",
                "area_id": "area-example",
                "labels": [],
            },
            {
                "id": "device-solo",
                "home_id": "home-example",
                "name": "Example standalone",
                "area_id": "area-example",
                "labels": [],
            },
        ],
    }
    assert value["bindings"] == {
        "schema_version": 1,
        "bindings": [
            {
                "home_id": "home-example",
                "device_id": "device-example",
                "provider": "ha",
                "provider_instance_id": "ha-example",
                "mapping": {
                    "entity_ids": ["sensor.example", "switch.example"],
                    "device_registry_id": "raw-device",
                },
            },
            {
                "home_id": "home-example",
                "device_id": "device-solo",
                "provider": "ha",
                "provider_instance_id": "ha-example",
                "mapping": {"entity_ids": ["sensor.solo"], "device_registry_id": None},
            },
        ],
    }
    assert Inventory.from_dict(value["inventory"]).to_dict() == value["inventory"]
    assert (
        BindingCollection.from_dict(value["bindings"], inventory=value["inventory"]).to_dict()
        == value["bindings"]
    )
    assert result.to_redacted_dict() == {
        "rules_version": 1,
        "counts": {
            "areas": 1,
            "devices": 2,
            "bindings": 2,
            "disabled_devices": 0,
            "disabled_entities": 0,
            "unassigned_areas": 0,
            "unassigned_devices": 0,
            "unassigned_entities": 0,
            "orphan_entities": 0,
            "unbound_devices": 0,
            "unresolved_areas": 0,
            "ignored_states": 0,
        },
    }


@pytest.mark.tc032_01
def test_order_repeated_calls_and_inputs_detached():
    config, data = configuration(), discovery()
    mapper = HARegistryMapper(config)
    original = copy.deepcopy(data)
    first = mapper.map(data).for_adapter()
    for rows in data.values():
        rows.reverse()
    assert mapper.map(data).for_adapter() == first
    assert sorted(data["entities"], key=lambda row: row["entity_id"]) == sorted(
        original["entities"], key=lambda row: row["entity_id"]
    )
    config["device_ids"]["raw-device"] = "other-device"
    assert mapper.map(data).for_adapter() == first
    first["bindings"]["bindings"][0]["mapping"]["entity_ids"].clear()
    assert mapper.map(data).for_adapter()["bindings"]["bindings"][0]["mapping"]["entity_ids"]
    result = mapper.map(data)
    exported = result.for_adapter()
    exported["inventory"]["devices"][0]["name"] = "mutated"
    assert result.for_adapter()["inventory"]["devices"][0]["name"] == "Example device"


@pytest.mark.tc032_01
def test_explicit_replacement_preserves_canonical_identity():
    config, data = configuration(), discovery()
    original = project(data, config).for_adapter()
    config["provider_instance_id"] = "ha-replacement"
    config["device_ids"] = {"replacement-device": "device-example"}
    config["entity_ids"] = {"sensor.replacement": "device-solo"}
    data["devices"][0]["id"] = "replacement-device"
    for row in data["entities"][:2]:
        row["device_id"] = "replacement-device"
    data["entities"][2]["entity_id"] = "sensor.replacement"
    changed = project(data, config).for_adapter()
    assert changed["inventory"] == original["inventory"]
    assert changed["bindings"]["bindings"][0]["mapping"]["device_registry_id"] == (
        "replacement-device"
    )
    assert all(
        row["provider_instance_id"] == "ha-replacement" for row in changed["bindings"]["bindings"]
    )


@pytest.mark.tc032_02
def test_removal_and_reappearance_are_fresh_projections():
    mapper, data = HARegistryMapper(configuration()), discovery()
    initial = mapper.map(data).for_adapter()
    data["entities"].pop(0)
    once = mapper.map(data).for_adapter()
    assert once["bindings"]["bindings"][0]["mapping"]["entity_ids"] == ["sensor.example"]
    data["entities"].pop(0)
    final = mapper.map(data)
    assert [d["id"] for d in final.for_adapter()["inventory"]["devices"]] == ["device-solo"]
    assert final.to_redacted_dict()["counts"]["unbound_devices"] == 1
    assert final.to_redacted_dict()["counts"]["ignored_states"] == 1
    assert mapper.map(discovery()).for_adapter() == initial


@pytest.mark.tc032_02
@pytest.mark.parametrize(
    "change,counts,device_count",
    [
        ("disabled_device", {"disabled_devices": 1, "orphan_entities": 2}, 1),
        ("disabled_entity", {"disabled_entities": 1}, 2),
        ("missing_device", {"orphan_entities": 2}, 1),
        ("unassigned_device", {"unassigned_devices": 1, "orphan_entities": 2}, 1),
        ("unassigned_entity", {"unassigned_entities": 1}, 1),
        ("unassigned_area", {"unassigned_areas": 1, "unresolved_areas": 2}, 2),
        ("missing_area", {"unresolved_areas": 2}, 2),
    ],
)
def test_disabled_missing_unassigned_policy(change, counts, device_count):
    config, data = configuration(), discovery()
    if change == "disabled_device":
        data["devices"][0]["disabled_by"] = "user"
    if change == "disabled_entity":
        data["entities"][0]["disabled_by"] = "integration"
    if change == "missing_device":
        data["devices"] = []
    if change == "unassigned_device":
        config["device_ids"] = {}
    if change == "unassigned_entity":
        config["entity_ids"] = {}
    if change == "unassigned_area":
        config["area_ids"] = {}
    if change == "missing_area":
        data["areas"] = []
    result = project(data, config)
    summary = result.to_redacted_dict()["counts"]
    for key, expected in counts.items():
        assert summary[key] == expected
    devices = result.for_adapter()["inventory"]["devices"]
    assert len(devices) == device_count
    if change in ("unassigned_area", "missing_area"):
        assert all(d["area_id"] is None for d in devices)


@pytest.mark.tc032_02
def test_entity_override_does_not_split_group_or_promote_orphan():
    config, data = configuration(), discovery()
    data["entities"][0]["area_id"] = "other-room"
    config["entity_ids"]["switch.example"] = "unused-id"
    result = project(data, config).for_adapter()
    assert len(result["inventory"]["devices"]) == 2
    assert result["inventory"]["devices"][0]["area_id"] == "area-example"
    data["devices"] = []
    result = project(data, config).for_adapter()
    assert [d["id"] for d in result["inventory"]["devices"]] == ["device-solo"]


@pytest.mark.tc032_02
@pytest.mark.parametrize(
    "names,expected",
    [
        ({"name_by_user": " User ", "name": "Registry"}, "User"),
        ({"name_by_user": " ", "name": "Registry"}, "Registry"),
        ({"name_by_user": None, "name": None}, "Device"),
        ({"name": ""}, "Device"),
    ],
)
def test_device_name_precedence(names, expected):
    data = discovery()
    data["devices"][0].update(names)
    assert project(data).for_adapter()["inventory"]["devices"][0]["name"] == expected


@pytest.mark.tc032_02
def test_empty_complete_input_and_states_never_create_or_delete_devices():
    empty = project({key: [] for key in discovery()}).for_adapter()
    assert empty["inventory"]["devices"] == [] and empty["bindings"]["bindings"] == []
    data = discovery()
    data["states"] = []
    before = project(data).for_adapter()
    data["states"] = [{"entity_id": "alien.entity", "state": "on", "attributes": {}}]
    result = project(data)
    assert result.for_adapter() == before
    assert result.to_redacted_dict()["counts"]["ignored_states"] == 1


@pytest.mark.tc032_03
@pytest.mark.parametrize("value", [None, [], True, {}, {"extra": 1}])
def test_invalid_top_level(value):
    for call, code in (
        (lambda: HARegistryMapper(value), "invalid_configuration"),
        (lambda: HARegistryMapper(configuration()).map(value), "invalid_discovery"),
    ):
        with pytest.raises(HAMappingError) as caught:
            call()
        assert caught.value.code == code and caught.value.__context__ is None


@pytest.mark.tc032_03
@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("provider_instance_id", "https://private"),
        ("area_ids", {"raw-room": "home-example"}),
        ("device_ids", {"raw-device": "area-example"}),
        ("entity_ids", {"sensor.solo": "device-example"}),
        ("device_ids", {"raw-device": "device-example", "other": "device-example"}),
        ("device_ids", {" raw-device": "device-example"}),
        ("device_ids", {"raw-device": "Not_Canonical"}),
        ("device_ids", {"x" * 513: "device-example"}),
        ("home", {"id": "home-example", "name": "private"}),
    ],
)
def test_configuration_rejects_ambiguity_and_malformed(field, value):
    config = configuration()
    config[field] = value
    with pytest.raises(HAMappingError, match="^invalid_configuration$"):
        HARegistryMapper(config)


@pytest.mark.tc032_03
@pytest.mark.parametrize("component", ["devices", "entities", "areas", "states"])
@pytest.mark.parametrize("problem", ["not_list", "duplicate", "missing_id", "wrong_id"])
def test_every_component_validated(component, problem):
    data = discovery()
    identity = {"devices": "id", "areas": "area_id"}.get(component, "entity_id")
    if problem == "not_list":
        data[component] = {}
    if problem == "duplicate":
        data[component].append(copy.deepcopy(data[component][0]))
    if problem == "missing_id":
        del data[component][0][identity]
    if problem == "wrong_id":
        data[component][0][identity] = False
    with pytest.raises(HAMappingError, match="^invalid_discovery$"):
        project(data)


@pytest.mark.tc032_03
@pytest.mark.parametrize(
    "component,field,value",
    [
        ("devices", "area_id", False),
        ("entities", "device_id", ""),
        ("entities", "disabled_by", 1),
        ("devices", "name", []),
        ("entities", "original_name", "x" * 513),
        ("areas", "name", ""),
        ("states", "state", False),
        ("states", "state", "x" * 4097),
        ("states", "attributes", []),
    ],
)
def test_known_fields_strict_even_if_not_projected(component, field, value):
    data = discovery()
    data[component][0][field] = value
    with pytest.raises(HAMappingError, match="^invalid_discovery$"):
        project(data)


@pytest.mark.tc032_03
@pytest.mark.parametrize("extra", [math.nan, math.inf, b"private", {1: "private"}, "\ud800"])
def test_unknown_fields_still_must_be_strict_json(extra):
    data = discovery()
    data["states"][0]["attributes"]["private"] = extra
    with pytest.raises(HAMappingError) as caught:
        project(data)
    assert caught.value.to_dict() == {"code": "invalid_discovery"}
    assert "private" not in repr(caught.value)
    assert caught.value.__context__ is None and caught.value.__cause__ is None


@pytest.mark.tc032_03
@pytest.mark.parametrize("problem", ["cycle", "alias", "depth", "nodes", "records", "bytes"])
def test_bounded_tree(problem):
    data = discovery()
    expected = "input_limit"
    if problem == "cycle":
        data["states"][0]["attributes"] = data
        expected = "invalid_discovery"
    if problem == "alias":
        data["states"][0]["attributes"] = data["devices"][0]
        expected = "invalid_discovery"
    if problem == "depth":
        nested = []
        for _ in range(33):
            nested = [nested]
        data["states"][0]["attributes"]["nested"] = nested
    if problem == "nodes":
        data["states"][0]["attributes"]["many"] = [0] * 200001
    if problem == "records":
        data["areas"] = [{"area_id": str(i), "name": "A"} for i in range(10001)]
    if problem == "bytes":
        data["states"][0]["attributes"]["large"] = "x" * (16 * 1024 * 1024)
    with pytest.raises(HAMappingError, match=f"^{expected}$"):
        project(data)


@pytest.mark.tc032_03
def test_immutable_redacted_and_serialization_refused():
    mapper = HARegistryMapper(configuration())
    result = mapper.map(discovery())
    for obj in (mapper, result, HAMappingError("invalid_discovery")):
        assert not any(s in repr(obj) for s in ("raw-device", "Example", "sensor.solo"))
        for method in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                method(obj)
    with pytest.raises(AttributeError):
        mapper._configuration = "private"
    with pytest.raises(AttributeError):
        result._inventory = "private"
    with pytest.raises(AttributeError):
        mapper.__init__(configuration())
    error = HAMappingError("invalid_discovery")
    with pytest.raises(AttributeError):
        error._code = "private"
    with pytest.raises(ValueError):
        HAMappingError("private")


@pytest.mark.tc032_03
def test_shared_validation_failure_is_private_and_does_not_poison_mapper(monkeypatch):
    mapper = HARegistryMapper(configuration())
    with monkeypatch.context() as patch:
        patch.setattr(
            BindingCollection,
            "from_dict",
            lambda *a, **kw: (_ for _ in ()).throw(ValueError("private provider identifier")),
        )
        with pytest.raises(HAMappingError) as caught:
            mapper.map(discovery())
        assert str(caught.value) == "invalid_projection"
        assert caught.value.__context__ is None
    assert mapper.map(discovery()).to_redacted_dict()["counts"]["devices"] == 2


@pytest.mark.tc032_03
def test_inputs_remain_unchanged_and_separate_homes_are_isolated():
    config, data = configuration(), discovery()
    saved = copy.deepcopy((config, data))
    first = project(data, config)
    assert (config, data) == saved
    config["home"]["id"] = "another-home"
    second = project(data, config).for_adapter()
    assert second["inventory"]["devices"][0]["home_id"] == "another-home"
    assert first.for_adapter()["inventory"]["devices"][0]["home_id"] == "home-example"
    assert json.dumps(first.to_redacted_dict()).find("raw-device") == -1


@pytest.mark.tc032_01
def test_discovery_snapshot_export_composes_without_raw_state_leak():
    from home_device_fabric.ha_discovery import HADiscoverySnapshot

    data = discovery()
    components = ("devices", "entities", "areas", "states")
    snapshot = HADiscoverySnapshot(
        tuple(json.dumps(data[key]) for key in components),
        tuple(len(data[key]) for key in components),
    )
    result = HARegistryMapper(configuration()).map(snapshot.for_mapping()).for_adapter()
    assert result == project().for_adapter()
    assert "attributes" not in json.dumps(result)


@pytest.mark.tc032_02
@pytest.mark.parametrize(
    "names,expected",
    [
        ({"name": "User", "original_name": "Original"}, "User"),
        ({"name": " ", "original_name": " Original "}, "Original"),
        ({"name": None, "original_name": None}, "Device"),
    ],
)
def test_standalone_names_and_null_locations(names, expected):
    data = discovery()
    data["entities"][2].update(names)
    data["entities"][2]["area_id"] = None
    value = project(data).for_adapter()["inventory"]["devices"][1]
    assert value["name"] == expected and value["area_id"] is None


@pytest.mark.tc032_03
@pytest.mark.parametrize("operation", ["inventory", "bindings"])
def test_process_control_propagates_without_translation(monkeypatch, operation):
    factory = Inventory if operation == "inventory" else BindingCollection

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()

    mapper = HARegistryMapper(configuration())
    monkeypatch.setattr(factory, "from_dict", interrupted)
    with pytest.raises(KeyboardInterrupt):
        mapper.map(discovery())


@pytest.mark.tc032_03
@pytest.mark.parametrize("boundary", ["assignments", "records"])
def test_10000_boundary_is_accepted_and_10001_is_rejected(boundary):
    config, data = configuration(), discovery()
    if boundary == "assignments":
        config["device_ids"] = {f"raw-{i}": f"device-{i}" for i in range(10000)}
        HARegistryMapper(config)
        config["device_ids"]["one-more"] = "extra-device"

        def call():
            return HARegistryMapper(config)
    else:
        data["devices"] = [{"id": f"raw-{i}"} for i in range(10000)]
        assert project(data).to_redacted_dict()["counts"]["unassigned_devices"] == 10000
        data["devices"].append({"id": "one-more"})

        def call():
            return project(data)

    with pytest.raises(HAMappingError, match="^input_limit$"):
        call()


@pytest.mark.tc032_03
@pytest.mark.parametrize("key", ["states", "extra"])
def test_incomplete_or_extra_component_rejected(key):
    data = discovery()
    if key == "states":
        del data[key]
    else:
        data[key] = []
    with pytest.raises(HAMappingError, match="^invalid_discovery$"):
        project(data)


@pytest.mark.tc032_03
def test_unknown_json_fields_are_tolerated_but_never_inferred():
    data = discovery()
    expected = project().for_adapter()
    data["devices"][0]["vendor"] = {"private": [None, False, 2, 2.5]}
    data["entities"][0]["capabilities"] = ["invented-action"]
    assert project(data).for_adapter() == expected


@pytest.mark.tc032_03
def test_result_reinitialization_refused():
    result = project()
    before = result.for_adapter()
    with pytest.raises(AttributeError):
        result.__init__("private", "private", ())
    assert result.for_adapter() == before
