"""TC-016-01: identity, JSON ingress, catalogue lookup and isolation."""

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest
from capability_support import capability_required, catalogue, changed, descriptor, reject

pytestmark = capability_required


def test_roundtrip_and_exact_lookup(capability_api):
    api = capability_api
    data = descriptor()
    other = changed(data, ("capability_version",), 2)
    records = api.CapabilityCatalogue.from_dict(catalogue(data, other))
    assert records.get("demo.power", 1).to_dict() == data
    assert records.get("demo.power", 2).to_dict() == other
    for version in (0, 3, True, 1.0, "1"):
        reject(api, lambda: records.get("demo.power", version))
    reject(api, lambda: records.get("unknown.power", 1))
    reject(api, lambda: api.validate_capabilities(catalogue(data, data)))
    assert api.validate_capabilities(catalogue()) == catalogue()
    assert api.load_capability_json(json.dumps(data)).to_dict() == data
    assert api.load_capabilities_json(json.dumps(catalogue(data))).to_dict() == catalogue(data)
    sensor = deepcopy(data)
    sensor["actions"] = sensor["events"] = {}
    assert api.validate_capability(sensor) == sensor
    sensor["properties"] = {}
    reject(api, lambda: api.validate_capability(sensor))


@pytest.mark.parametrize("field", list(descriptor()))
def test_required_descriptor_keys(capability_api, field):
    data = descriptor()
    del data[field]
    reject(capability_api, lambda: capability_api.validate_capability(data), (field,))


@pytest.mark.parametrize("value", [True, 1.0, "1", None, 0, 2, -1])
def test_schema_version(capability_api, value):
    data = changed(descriptor(), ("schema_version",), value)
    reject(capability_api, lambda: capability_api.validate_capability(data), ("schema_version",))
    reject(
        capability_api,
        lambda: capability_api.validate_capabilities({"schema_version": value, "capabilities": []}),
    )


@pytest.mark.parametrize("value", [True, 1.0, "1", None, 0, -1])
def test_capability_revision(capability_api, value):
    reject(
        capability_api,
        lambda: capability_api.validate_capability(
            changed(descriptor(), ("capability_version",), value)
        ),
        ("capability_version",),
    )


@pytest.mark.parametrize(
    "value,valid",
    [
        ("power", False),
        ("demo.power", True),
        ("a.b.c.d", True),
        ("a.b.c.d.e", False),
        ("a" * 32 + ".b", True),
        ("a" * 33 + ".b", False),
        ("a.b" + "x" * 31, True),
        ("a.b" + "x" * 32, False),
        ("Demo.power", False),
        ("demo.power\n", False),
        ("demo.1power", False),
        ("demo..power", False),
        ("demo-power", False),
        ("demo.é", False),
        ("demo._power", False),
        ("a.b_0", True),
    ],
)
def test_id_boundaries(capability_api, value, valid):
    data = changed(descriptor(), ("capability_id",), value)
    if valid:
        assert capability_api.validate_capability(data) == data
    else:
        reject(capability_api, lambda: capability_api.validate_capability(data))


@pytest.mark.parametrize(
    "path,limit",
    [
        (("title",), 256),
        (("description",), 2048),
        *(
            (("properties", "power", field), limit)
            for field, limit in [("title", 256), ("description", 2048)]
        ),
        *(
            (("actions", "set_power", field), limit)
            for field, limit in [("title", 256), ("description", 2048)]
        ),
        *(
            (("events", "changed", field), limit)
            for field, limit in [("title", 256), ("description", 2048)]
        ),
    ],
)
def test_text_limits(capability_api, path, limit):
    assert capability_api.validate_capability(changed(descriptor(), path, "x" * limit))
    for value in ("", " \t\n", "x" * (limit + 1), None, 1):
        reject(
            capability_api,
            lambda: capability_api.validate_capability(changed(descriptor(), path, value)),
            path,
        )


@pytest.mark.parametrize("container", ["properties", "actions", "events"])
@pytest.mark.parametrize(
    "name,valid",
    [
        ("a", True),
        ("a" * 64, True),
        ("a" * 65, False),
        ("demo.power", False),
        ("Upper", False),
        ("a\n", False),
    ],
)
def test_member_names(capability_api, container, name, valid):
    data = descriptor()
    # Remove action references so renaming a member tests naming alone.
    data["actions"]["set_power"]["completion_policy"] = {"kind": "ack_only"}
    data[container] = {name: next(iter(data[container].values()))}
    if valid:
        assert capability_api.validate_capability(data)
    else:
        reject(
            capability_api,
            lambda: capability_api.validate_capability(data),
            (container, "<property>"),
        )


@pytest.mark.parametrize(
    "text",
    [
        '{"schema_version":1,"schema_version":1}',
        '{"x":{"PRIVATE_DUPLICATE":1,"PRIVATE_DUPLICATE":2}}',
        '{"x":[{"a":1,"a":2}]}',
        "NaN",
        "Infinity",
        "-Infinity",
        "{",
        '"PRIVATE_TEXT" trailing',
        None,
        b"{}",
    ],
)
def test_bad_text(capability_api, text):
    for loader in (capability_api.load_capability_json, capability_api.load_capabilities_json):
        reject(capability_api, lambda: loader(text), private=("PRIVATE_DUPLICATE", "PRIVATE_TEXT"))


def test_immutable_detached_snapshots(capability_api):
    data = descriptor()
    original = deepcopy(data)
    parsed = capability_api.CapabilityDescriptor.from_dict(data)
    data["actions"]["set_power"]["input_schema"]["required"].clear()
    out = parsed.to_dict()
    out["properties"]["power"]["value_schema"]["type"] = "null"
    assert parsed.to_dict() == original
    with pytest.raises(FrozenInstanceError):
        parsed.title = "changed"
    with pytest.raises(FrozenInstanceError):
        parsed.actions[0][1].input_schema.kind = "null"
    parsed_catalogue = capability_api.CapabilityCatalogue.from_dict(catalogue(original))
    snap = parsed_catalogue.to_dict()
    snap["capabilities"].clear()
    assert parsed_catalogue.to_dict() == catalogue(original)


@pytest.mark.parametrize(
    "path", [(), ("properties", "power"), ("actions", "set_power"), ("events", "changed")]
)
def test_private_unknown_key(capability_api, path):
    data = descriptor()
    target = data
    for part in path:
        target = target[part]
    target["PRIVATE_KEY"] = "PRIVATE_VALUE"
    reject(
        capability_api,
        lambda: capability_api.validate_capability(data),
        (*path, "<unknown>"),
        ("PRIVATE_KEY", "PRIVATE_VALUE"),
    )


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {},
        {"schema_version": 1},
        {"schema_version": 1, "capabilities": {}},
        {"schema_version": 1, "capabilities": [None]},
        {"schema_version": 1, "capabilities": [], "PRIVATE_KEY": "PRIVATE_VALUE"},
        {1: "PRIVATE_VALUE"},
    ],
)
def test_malformed_catalogues(capability_api, data):
    reject(
        capability_api,
        lambda: capability_api.validate_capabilities(data),
        private=("PRIVATE_KEY", "PRIVATE_VALUE"),
    )


@pytest.mark.parametrize("container", ["properties", "actions", "events"])
@pytest.mark.parametrize("value", [None, [], False, {1: {}}])
def test_interaction_maps(capability_api, container, value):
    reject(
        capability_api,
        lambda: capability_api.validate_capability(changed(descriptor(), (container,), value)),
    )


def test_duplicate_keys_have_specific_safe_diagnostic(capability_api):
    text = json.dumps(descriptor()).replace(
        '"type": "boolean"', '"type": "boolean", "type": "boolean"', 1
    )
    with pytest.raises(capability_api.CapabilityError) as caught:
        capability_api.load_capability_json(text)
    assert caught.value.path == ("<unknown>",)
    assert caught.value.message == "duplicate JSON object key"
    # The already-parsed path cannot claim duplicate-key detection.
    parsed = json.loads(text)
    assert capability_api.validate_capability(parsed) == descriptor()


def test_catalogue_payload_selection(capability_api):
    old = descriptor()
    newer = changed(old, ("capability_version",), 2)
    newer["actions"]["set_power"]["input_schema"]["properties"]["power"] = {"type": "integer"}
    newer["properties"]["power"]["value_schema"] = {"type": "integer"}
    parsed = capability_api.CapabilityCatalogue.from_dict(catalogue(old, newer))
    assert parsed.validate_payload(
        "demo.power", 1, "action_input", "set_power", {"power": False}
    ) == {"power": False}
    assert parsed.validate_payload("demo.power", 2, "action_input", "set_power", {"power": 0}) == {
        "power": 0
    }
    reject(
        capability_api,
        lambda: parsed.validate_payload(
            "demo.power", 2, "action_input", "set_power", {"power": False}
        ),
    )
    reject(
        capability_api,
        lambda: parsed.validate_payload("demo.power", 3, "action_input", "set_power", {"power": 0}),
    )


def test_public_catalogue_fixture(capability_api):
    from inventory_support import ROOT

    path = ROOT / "docs/product/home-intelligence/examples/capability-base.example.json"
    parsed = capability_api.load_capabilities_json(path.read_text())
    assert parsed.to_dict() == catalogue(descriptor())
