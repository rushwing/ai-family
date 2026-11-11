"""REQ-038 generator-proposed criteria; independent combined review pending."""

import builtins
import copy
import json
import os
import pickle
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from action_resolution_artifact_smoke import check, configuration, entry, request
from home_device_fabric.action_resolution import ActionResolutionError, ActionResolver
from home_device_fabric.ha_mapping import _json
from home_device_fabric.mock import MockProvider


@pytest.fixture(autouse=True)
def no_provider_calls(monkeypatch):
    calls = []

    def deny(*args, **kwargs):
        calls.append(1)
        raise AssertionError("provider forbidden")

    for name in ("discover", "snapshot", "submit", "advance", "settle"):
        monkeypatch.setattr(MockProvider, name, deny)
    yield calls
    assert calls == []


@pytest.fixture
def config():
    return configuration()


@pytest.fixture
def resolver(config):
    return ActionResolver(**config)


@pytest.mark.tc038_01
@pytest.mark.parametrize("value", [True, False])
def test_exact_grouped_switch_plan(resolver, value, offline):
    raw = request(arguments={"is_on": value})
    assert resolver.resolve(raw).for_adapter() == {"status": "resolved", "failure_code": None,
        "request": raw, "operation": {"provider": "ha", "provider_instance_id": "ha-example",
        "domain": "switch", "service": "turn_on" if value else "turn_off",
        "target": {"entity_id": "switch.example"}, "service_data": {}}}
    assert offline == []


@pytest.mark.tc038_01
@pytest.mark.parametrize("value", [0, 50, 100])
def test_exact_grouped_curtain_plan(resolver, value):
    raw = request(capability_id="home.positionable", action_id="set_position",
                  arguments={"position_percent": value})
    assert resolver.resolve(raw).for_adapter() == {"status": "resolved", "failure_code": None,
        "request": raw, "operation": {"provider": "ha", "provider_instance_id": "ha-example",
        "domain": "cover", "service": "set_cover_position",
        "target": {"entity_id": "cover.example"}, "service_data": {"position": value}}}


@pytest.mark.tc038_01
def test_exact_entity_not_first_binding_member_and_correlation(resolver, config):
    config["bindings"]["bindings"][0]["mapping"]["entity_ids"].reverse()
    other = ActionResolver(**config)
    raw = request(trace_id="trace-next", idempotency_key="key-next")
    assert resolver.resolve(raw).for_adapter() == other.resolve(raw).for_adapter()
    raw = request(device_id="device-other")
    assert resolver.resolve(raw).for_adapter()["operation"]["target"] == {
        "entity_id": "switch.other"}


@pytest.mark.tc038_02
def test_missing_internal_entry_fails_closed_without_changing_precedence(resolver, offline):
    # Fault injection bypasses the frozen snapshot; public construction cannot
    # create a validator/entry mismatch. Preserve other entries to catch fallback.
    object.__setattr__(resolver, "_entries", tuple(
        row for row in resolver._entries if row[:3] != (
            "device-example", "home.switchable", 1)))
    result = resolver.resolve(request())
    assert result.for_adapter() == {"status": "rejected",
        "failure_code": "unsupported_operation", "request": None, "operation": None}
    assert result.to_redacted_dict() == {
        "status": "rejected", "failure_code": "unsupported_operation"}
    assert resolver.resolve(request(arguments={"is_on": 1})).failure_code == "invalid_arguments"
    assert resolver.resolve(request(device_id="device-other")).status == "resolved"
    object.__setattr__(resolver, "_bindings", ())
    assert resolver.resolve(request()).failure_code == "missing_binding"
    assert offline == []


@pytest.mark.tc038_02
@pytest.mark.parametrize("changes,code", [
    ({"home_id": "home-other", "device_id": "missing"}, "unknown_home"),
    ({"device_id": "missing", "capability_id": "vendor.private"}, "unknown_device"),
    ({"capability_id": "vendor.private"}, "unknown_capability"),
    ({"capability_version": 2}, "unsupported_capability_version"),
    ({"action_id": "toggle"}, "unknown_action"),
    ({"arguments": {"is_on": 1}}, "invalid_arguments"),
    ({"extra": "private"}, "invalid_request"),
])
def test_semantic_errors_precede_missing_binding(config, changes, code):
    config["bindings"]["bindings"] = []
    assert ActionResolver(**config).resolve(request(**changes)).for_adapter() == {
        "status": "rejected", "failure_code": code, "request": None, "operation": None}


@pytest.mark.tc038_02
@pytest.mark.parametrize("kind,code", [("binding", "missing_binding"),
    ("instance", "provider_mismatch"), ("mock", "provider_mismatch"),
    ("map", "mapping_uninitialized"), ("metadata", "capabilities_uninitialized"),
    ("empty_metadata", "unknown_capability")])
def test_absent_or_mismatched_configuration_fails_closed(config, kind, code):
    if kind == "binding":
        config["bindings"]["bindings"] = []
    elif kind == "instance":
        config["provider_instance_id"] = "ha-other"
    elif kind == "mock":
        binding = config["bindings"]["bindings"][0]
        binding.update(provider="mock", mapping={"device_key": "private"})
    elif kind == "map":
        entry(config)["provider_mapping"] = None
    elif kind == "metadata":
        config["capability_projection"]["devices"] = []
    else:
        config["capability_projection"]["devices"][0]["capabilities"] = []
    result = ActionResolver(**config).resolve(request())
    assert result.for_adapter() == {"status": "rejected", "failure_code": code,
                                    "request": None, "operation": None}


@pytest.mark.tc038_02
@pytest.mark.parametrize("capability", ["home.temperature_sensor", "home.humidity_sensor",
                                        "home.power_meter", "home.battery_powered"])
def test_read_only_before_binding(config, capability):
    config["bindings"]["bindings"] = []
    result = ActionResolver(**config).resolve(request(capability_id=capability, action_id="set_on"))
    assert result.failure_code == "read_only_capability"


@pytest.mark.tc038_02
@pytest.mark.parametrize("field,value", [
    ("entity_id", "switch.other"), ("entity_id", "cover.example"),
    ("entity_id", "switch.example/../../service"), ("entity_id", "switch.EXAMPLE"),
    ("entity_id", "switch.温度"), ("entity_id", ["switch.example"]),
    ("provider", "mock"), ("provider_instance_id", "ha-other"),
    ("actions", {}), ("properties", {}), ("private-extra", "private-secret"),
])
def test_unregistered_cross_device_or_hostile_map_rejected(config, field, value):
    entry(config)["provider_mapping"][field] = value
    result = ActionResolver(**config).resolve(request())
    assert result.for_adapter() == {"status": "rejected",
        "failure_code": "invalid_provider_mapping", "request": None, "operation": None}
    assert "private" not in json.dumps(result.to_redacted_dict()) + repr(result)


@pytest.mark.tc038_02
@pytest.mark.parametrize("kind", ["service", "selector", "parameters", "service_data",
                                   "additional_action", "missing_field"])
def test_service_and_parameter_overrides_never_executed(config, kind):
    mapping = entry(config)["provider_mapping"]
    if kind == "additional_action":
        mapping["actions"]["unlock"] = {}
    elif kind == "missing_field":
        del mapping["properties"]
    else:
        mapping["actions"]["set_on"][kind] = "private-secret"
    assert ActionResolver(**config).resolve(request()).failure_code == "invalid_provider_mapping"


@pytest.mark.tc038_02
@pytest.mark.parametrize("kind", ["new_version", "changed_descriptor", "custom_capability",
                                   "new_action"])
def test_only_fixed_supported_descriptor_and_revision(config, kind):
    item = entry(config)
    changes = {}
    if kind == "new_version":
        item["descriptor"]["capability_version"] = 2
        changes["capability_version"] = 2
    elif kind == "changed_descriptor":
        item["descriptor"]["title"] = "Private altered title"
    elif kind == "custom_capability":
        item["descriptor"]["capability_id"] = "vendor.custom"
        changes["capability_id"] = "vendor.custom"
    else:
        item["descriptor"]["actions"]["toggle"] = copy.deepcopy(
            item["descriptor"]["actions"]["set_on"])
        changes["action_id"] = "toggle"
    assert ActionResolver(**config).resolve(request(**changes)).failure_code == (
        "unsupported_operation")


@pytest.mark.tc038_02
@pytest.mark.parametrize("arguments", [{}, {"is_on": 1}, {"is_on": "true"},
    {"is_on": True, "entity_id": "switch.other"}, {"is_on": True, "service": "unlock"}])
def test_request_cannot_override_provider_operation(resolver, arguments):
    assert resolver.resolve(request(arguments=arguments)).failure_code == "invalid_arguments"


@pytest.mark.tc038_02
@pytest.mark.parametrize("value", [-1, 101, True, False, 50.0, 50.5, "50", None])
def test_curtain_no_coercion_rounding_or_range_escape(resolver, value):
    assert resolver.resolve(request(capability_id="home.positionable", action_id="set_position",
        arguments={"position_percent": value})).failure_code == "invalid_arguments"


@pytest.mark.tc038_03
@pytest.mark.parametrize("kind", ["inventory", "binding_reference", "duplicate_binding",
    "duplicate_resource", "duplicate_device", "unknown_device", "home", "duplicate_capability",
    "bad_descriptor", "envelope", "rules_bool", "rules_version", "devices", "record",
    "entry", "map_scalar", "projection_alias", "cycle", "typed_inventory", "alias",
    "bool_limit", "zero_limit", "large_limit", "float_limit"])
def test_invalid_configuration_fixed_error_without_chain(config, kind):
    projection = config["capability_projection"]
    if kind == "inventory":
        config["registered_inventory"]["private-extra"] = "private-secret"
    elif kind == "binding_reference":
        config["bindings"]["bindings"][0]["device_id"] = "device-missing"
    elif kind == "duplicate_binding":
        config["bindings"]["bindings"].append(copy.deepcopy(config["bindings"]["bindings"][0]))
    elif kind == "duplicate_resource":
        config["bindings"]["bindings"][1]["mapping"]["entity_ids"] = ["switch.example"]
    elif kind == "duplicate_device":
        projection["devices"].append(copy.deepcopy(projection["devices"][0]))
    elif kind == "unknown_device":
        projection["devices"][0]["device_id"] = "device-missing"
    elif kind == "home":
        projection["devices"][0]["home_id"] = "home-other"
    elif kind == "duplicate_capability":
        projection["devices"][0]["capabilities"].append(copy.deepcopy(entry(config)))
    elif kind == "bad_descriptor":
        entry(config)["descriptor"]["private-extra"] = "private-secret"
    elif kind == "envelope":
        projection["private-extra"] = "private-secret"
    elif kind in ("rules_bool", "rules_version"):
        projection["rules_version"] = True if kind == "rules_bool" else 2
    elif kind == "devices":
        projection["devices"] = {}
    elif kind == "record":
        projection["devices"][0]["private-extra"] = "private-secret"
    elif kind == "entry":
        entry(config)["private-extra"] = "private-secret"
    elif kind == "map_scalar":
        entry(config)["provider_mapping"] = "private-secret"
    elif kind == "projection_alias":
        projection["devices"].append(projection["devices"][0])
    elif kind == "cycle":
        entry(config)["provider_mapping"]["private-secret"] = projection
    elif kind == "typed_inventory":
        from state_schema.home_inventory import Inventory
        config["registered_inventory"] = Inventory.from_dict(config["registered_inventory"])
    elif kind == "alias":
        config["provider_instance_id"] = "https://private-secret"
    else:
        config["max_input_bytes"] = {"bool_limit": True, "zero_limit": 0,
            "large_limit": 16777217, "float_limit": 100.0}[kind]
    with pytest.raises(ActionResolutionError, match="^invalid_configuration$") as caught:
        ActionResolver(**config)
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert "private" not in str(caught.value) + repr(caught.value)


@pytest.mark.tc038_03
@pytest.mark.parametrize("kind", ["cycle", "alias", "subclass", "depth", "nonstring_key",
                                   "typed_request", "nan", "integer"])
def test_hostile_plain_json(config, resolver, kind):
    raw = request()
    if kind == "cycle":
        raw["arguments"] = raw
    elif kind == "alias":
        shared = []
        raw["arguments"] = {"one": shared, "two": shared}
    elif kind == "subclass":
        class Custom(dict):
            pass
        raw = Custom(raw)
    elif kind == "depth":
        for _ in range(40):
            raw = {"nested": raw}
    elif kind == "nonstring_key":
        raw[1] = "private"
    elif kind == "typed_request":
        from state_schema.action_contracts import ActionRequest
        raw = ActionRequest.from_dict(raw)
    else:
        raw["arguments"] = {"is_on": float("nan") if kind == "nan" else 1 << 5000}
    assert resolver.resolve(raw).failure_code == "invalid_request"


@pytest.mark.tc038_03
def test_exact_byte_boundaries_and_unicode(config):
    raw = request()
    size = len(_json(raw).encode("utf-8"))
    assert ActionResolver(**config, max_input_bytes=size).resolve(raw).status == "resolved"
    assert ActionResolver(**config, max_input_bytes=size - 1).resolve(raw).failure_code == (
        "input_too_large")
    raw["private"] = "温度" * 100
    assert ActionResolver(**config, max_input_bytes=size).resolve(raw).failure_code == (
        "input_too_large")


@pytest.mark.tc038_03
def test_snapshot_and_exports_detached_immutable(config):
    before = copy.deepcopy(config)
    resolver = ActionResolver(**config)
    assert config == before
    config["bindings"]["bindings"].clear()
    entry(config)["provider_mapping"]["actions"].clear()
    raw = request()
    result = resolver.resolve(raw)
    raw["arguments"]["is_on"] = False
    exported = result.for_adapter()
    exported["request"]["arguments"]["is_on"] = False
    exported["operation"]["target"]["entity_id"] = "private"
    assert result.for_adapter()["request"] == request()
    assert result.for_adapter()["operation"]["target"] == {"entity_id": "switch.example"}
    for obj, field in ((resolver, "_instance"), (result, "failure_code")):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, "private")
    with pytest.raises(AttributeError, match="immutable_action_resolver"):
        resolver.__init__(**before)


@pytest.mark.tc038_03
@pytest.mark.parametrize("copier", [copy.copy, copy.deepcopy, pickle.dumps])
def test_repr_summary_and_serialization_never_export_payload(resolver, copier):
    for obj, code in ((resolver, "action_resolver_serialization_forbidden"),
        (resolver.resolve(request()), "action_resolution_result_serialization_forbidden"),
        (resolver.resolve(request(home_id="private")),
         "action_resolution_result_serialization_forbidden")):
        with pytest.raises(TypeError, match="^" + code + "$"):
            copier(obj)
        assert all(text not in repr(obj)
                   for text in ("ha-example", "switch.example", "home-example"))
    assert resolver.resolve(request()).to_redacted_dict() == {
        "status": "resolved", "failure_code": None}


@pytest.mark.tc038_03
def test_concurrent_instances_and_calls_are_isolated(config, resolver):
    config["bindings"]["bindings"] = []
    unbound = ActionResolver(**config)

    def resolve(i):
        return (resolver if i % 2 else unbound).resolve(request()).failure_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(resolve, range(100))) == [
            None if i % 2 else "missing_binding" for i in range(100)]


@pytest.mark.tc038_03
def test_resolution_no_file_env_effect_even_if_swallowed(resolver, monkeypatch, offline):
    calls = []

    def deny(*args, **kwargs):
        calls.append(1)
        raise AssertionError("file/env forbidden")

    with monkeypatch.context() as guard:
        for module, names in ((builtins, ("open",)), (Path, ("open", "read_text", "read_bytes")),
                              (os, ("getenv",))):
            for name in names:
                guard.setattr(module, name, deny)
        assert resolver.resolve(request()).status == "resolved"
        assert resolver.resolve(request(action_id="unlock")).status == "rejected"
        assert resolver.resolve(request(device_id="missing")).status == "rejected"
    assert calls == [] and offline == []


@pytest.mark.tc038_04
def test_installed_smoke_contract(offline):
    assert check() == {"checks": 27, "offline": True}
    assert offline == []
