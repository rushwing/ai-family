"""TC-016-02: actual schemas and payloads with independently counted depths."""

from copy import deepcopy

import pytest
from capability_support import capability_required, descriptor, obj, reject

pytestmark = capability_required


@pytest.mark.parametrize(
    "schema,good,bad",
    [
        ({"type": "boolean"}, False, 0),
        ({"type": "integer"}, 0, False),
        ({"type": "integer"}, 5, 5.0),
        ({"type": "number"}, 0.0, True),
        ({"type": "number"}, 0, float("nan")),
        ({"type": "string"}, "", None),
        ({"type": "null"}, None, ""),
        ({"type": "array", "items": {"type": "integer"}}, [1, 2], [True]),
        (obj({"power": {"type": "boolean"}}), {"power": False}, {"power": 0}),
        ({"type": "integer", "minimum": 0, "maximum": 2}, 2, -1),
        ({"type": "number", "minimum": 0.0, "maximum": 2.0}, 0, 3),
        ({"type": "string", "minLength": 1, "maxLength": 2}, "ab", ""),
        ({"type": "array", "items": {"type": "null"}, "minItems": 1, "maxItems": 2}, [None], []),
        ({"type": "string", "enum": ["off", "on"]}, "off", "OFF"),
        ({"type": "boolean", "enum": [False]}, False, 0),
        ({"type": "number", "enum": [0]}, 0.0, True),
        ({"type": "null", "enum": [None]}, None, False),
    ],
)
def test_schema_payload_cases(capability_api, schema, good, bad):
    assert capability_api.validate_schema(schema) == schema
    assert capability_api.validate_payload(schema, good) == good
    reject(capability_api, lambda: capability_api.validate_payload(schema, bad))


@pytest.mark.parametrize(
    "schema,bad,constraint",
    [
        ({"type": "integer", "minimum": 0}, -1, "minimum"),
        ({"type": "integer", "maximum": 2}, 3, "maximum"),
        ({"type": "number", "minimum": 0.0}, -0.5, "minimum"),
        ({"type": "number", "maximum": 2.0}, 2.5, "maximum"),
        ({"type": "string", "minLength": 20}, "PRIVATE_PAYLOAD", "minLength"),
        ({"type": "string", "maxLength": 2}, "PRIVATE_PAYLOAD", "maxLength"),
        ({"type": "array", "items": {"type": "null"}, "minItems": 1}, [], "minItems"),
        ({"type": "array", "items": {"type": "null"}, "maxItems": 1}, [None, None], "maxItems"),
    ],
)
@pytest.mark.parametrize("location", ["root", "object", "array"])
def test_payload_bound_diagnostics(capability_api, schema, bad, constraint, location):
    path = ()
    if location == "object":
        schema, bad = obj({"value": schema}), {"value": bad}
        path = ("value",)
    elif location == "array":
        schema, bad = {"type": "array", "items": schema}, [bad]
        path = (0,)
    original_schema, original_payload = deepcopy(schema), deepcopy(bad)
    record = capability_api.Schema.from_dict(schema)
    for validate in (record.validate, lambda value: capability_api.validate_payload(schema, value)):
        reject(
            capability_api,
            lambda: validate(bad),
            (*path, constraint),
            private=("PRIVATE_PAYLOAD",),
        )
    assert schema == original_schema and bad == original_payload
    assert record.to_dict() == original_schema


@pytest.mark.parametrize(
    "schema",
    [
        {},
        {"type": True},
        {"type": ["string"]},
        {"type": "unknown"},
        {"type": "boolean", "minimum": 0},
        {"type": "null", "minLength": 0},
        {"type": "integer", "minimum": True},
        {"type": "integer", "minimum": 0.0},
        {"type": "number", "maximum": float("inf")},
        {"type": "integer", "minimum": 2, "maximum": 1},
        {"type": "string", "minLength": -1},
        {"type": "string", "maxLength": True},
        {"type": "string", "minLength": 2, "maxLength": 1},
        {"type": "array", "items": []},
        {"type": "array", "items": {"type": "null"}, "minItems": 2, "maxItems": 1},
        {"type": "array", "items": {"type": "null"}, "maxItems": 1.0},
        {"type": "number", "enum": [0, 0.0]},
        {"type": "boolean", "enum": [False, 0]},
        {"type": "integer", "enum": [1, True]},
        {"type": "integer", "enum": [1, 1]},
        {"type": "string", "enum": []},
        {"type": "integer", "enum": [0], "minimum": 1},
        {"type": "number", "enum": [float("nan")]},
        {"type": "null", "enum": [None, None]},
        obj({"a": {"type": "integer"}}, ["missing"]),
        obj({"a": {"type": "integer"}}, ["a", "a"]),
        {**obj(), "additionalProperties": True},
        {**obj(), "required": "a"},
        {**obj(), "properties": {"PRIVATE_SCHEMA_NAME": {"type": "null"}}},
        {"type": "array"},
        {"type": "object"},
    ],
)
def test_malformed_schemas(capability_api, schema):
    reject(
        capability_api,
        lambda: capability_api.validate_schema(schema),
        private=("PRIVATE_SCHEMA_NAME",),
    )


@pytest.mark.parametrize(
    "keyword",
    [
        "$ref",
        "$id",
        "$schema",
        "default",
        "format",
        "pattern",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "PRIVATE_KEYWORD",
    ],
)
def test_unknown_keywords(capability_api, keyword):
    reject(
        capability_api,
        lambda: capability_api.validate_schema({"type": "string", keyword: "PRIVATE_SCHEMA_VALUE"}),
        ("<unknown>",),
        ("PRIVATE_KEYWORD", "PRIVATE_SCHEMA_VALUE"),
    )


def test_object_optionality_isolation_and_selection(capability_api):
    schema = obj(
        {"a": {"type": "integer"}, "b": {"type": "array", "items": {"type": "null"}}}, ["a"]
    )
    assert capability_api.validate_payload(schema, {"a": 0}) == {"a": 0}
    for data in ({}, {"a": 0, "PRIVATE_EXTRA": 1}, {"a": 0, "b": [0]}, {1: 0}):
        reject(
            capability_api,
            lambda: capability_api.validate_payload(schema, data),
            private=("PRIVATE_EXTRA",),
        )
    payload = {"a": 0, "b": [None]}
    snapshot = deepcopy(payload)
    validated = capability_api.validate_payload(schema, payload)
    validated["b"].clear()
    assert payload == snapshot
    d = capability_api.CapabilityDescriptor.from_dict(descriptor())
    for kind, name, payload in [
        ("property", "power", False),
        ("action_input", "set_power", {"power": False}),
        ("action_output", "set_power", {"accepted": True}),
        ("event", "changed", {"power": False}),
    ]:
        assert d.validate_payload(kind, name, payload) == payload
        reject(capability_api, lambda: d.validate_payload(kind, name, []))
        reject(
            capability_api,
            lambda: d.validate_payload(kind, "PRIVATE_MEMBER", payload),
            private=("PRIVATE_MEMBER",),
        )
    reject(capability_api, lambda: d.validate_payload("execute", "set_power", {}))


@pytest.mark.parametrize("depth,valid", [(1, True), (16, True), (17, False)])
@pytest.mark.parametrize("container", ["array", "object"])
def test_depth_nodes(capability_api, depth, valid, container):
    schema = {"type": "null"}
    value = None
    for _ in range(depth - 1):
        if container == "array":
            schema = {"type": "array", "items": schema}
            value = [value]
        else:
            schema = obj({"child": schema})
            value = {"child": value}
    if valid:
        assert capability_api.validate_schema(schema) == schema
        assert capability_api.validate_payload(schema, value) == value
    else:
        reject(capability_api, lambda: capability_api.validate_schema(schema))
    # Payload depth validation is independent of schema matching: this payload
    # fails the scalar schema but depth 17 must specifically trip the JSON guard.
    if depth == 17:
        with pytest.raises(capability_api.CapabilityError) as caught:
            capability_api.validate_payload({"type": "null"}, value)
        assert "depth" in caught.value.message


def test_cycles_and_non_json(capability_api):
    schema = {"type": "array"}
    schema["items"] = schema
    reject(capability_api, lambda: capability_api.validate_schema(schema))
    value = []
    value.append(value)
    reject(capability_api, lambda: capability_api.validate_payload({"type": "null"}, value))
    for value in (float("inf"), float("-inf"), object(), (1,), {1: 2}):
        reject(capability_api, lambda: capability_api.validate_payload({"type": "null"}, value))
    shared = [None]
    assert capability_api.validate_payload(
        {"type": "array", "items": {"type": "array", "items": {"type": "null"}}}, [shared, shared]
    ) == [[None], [None]]


def test_no_args_no_result(capability_api):
    data = descriptor()
    action = data["actions"]["set_power"]
    action.update(
        input_schema=obj(), output_schema={"type": "null"}, completion_policy={"kind": "ack_only"}
    )
    parsed = capability_api.CapabilityDescriptor.from_dict(data)
    assert parsed.validate_payload("action_input", "set_power", {}) == {}
    assert parsed.validate_payload("action_output", "set_power", None) is None
    reject(
        capability_api,
        lambda: parsed.validate_payload("action_input", "set_power", {"power": False}),
    )


@pytest.mark.parametrize(
    "kind", ["boolean", "integer", "number", "string", "null", "object", "array"]
)
def test_schema_required_and_inapplicable_fields(capability_api, kind):
    valid = {"type": kind}
    if kind == "object":
        valid = obj({"optional": {"type": "null"}}, [])
    elif kind == "array":
        valid["items"] = {"type": "null"}
    for field in valid:
        malformed = deepcopy(valid)
        del malformed[field]
        reject(capability_api, lambda: capability_api.validate_schema(malformed))
    reject(
        capability_api,
        lambda: capability_api.validate_schema({**valid, "PRIVATE_KEY": None}),
        private=("PRIVATE_KEY",),
    )


@pytest.mark.parametrize("value", [True, False, 1.0, -1, "1", None])
@pytest.mark.parametrize("constraint", ["minLength", "maxLength", "minItems", "maxItems"])
def test_length_constraint_types(capability_api, value, constraint):
    schema = (
        {"type": "string"}
        if constraint.endswith("Length")
        else {"type": "array", "items": {"type": "null"}}
    )
    schema[constraint] = value
    reject(capability_api, lambda: capability_api.validate_schema(schema))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, None, "0"])
@pytest.mark.parametrize("constraint", ["minimum", "maximum"])
def test_numeric_constraint_types(capability_api, value, constraint):
    reject(
        capability_api,
        lambda: capability_api.validate_schema({"type": "number", constraint: value}),
    )


def test_depth_16_schema_survives_text_wrappers(capability_api):
    schema = {"type": "null"}
    value = None
    for _ in range(15):
        schema = {"type": "array", "items": schema}
        value = [value]
    data = descriptor()
    data["events"]["changed"]["data_schema"] = schema
    import json

    parsed = capability_api.load_capability_json(json.dumps(data))
    assert parsed.validate_payload("event", "changed", value) == value
    for _ in range(1200):
        value = [value]
    reject(capability_api, lambda: capability_api.validate_payload({"type": "null"}, value))
    reject(
        capability_api,
        lambda: capability_api.load_capability_json("[" * 1200 + "null" + "]" * 1200),
    )


def test_internal_records_are_revalidated_at_payload_boundaries(capability_api):
    from dataclasses import replace

    api = capability_api
    parsed = api.CapabilityDescriptor.from_dict(descriptor())
    corrupt = replace(parsed, schema_version=2)
    reject(api, lambda: corrupt.validate_payload("property", "power", False))
    corrupt_schema = api.Schema("unsupported")
    reject(api, lambda: corrupt_schema.validate(None))
    corrupt_catalogue = api.CapabilityCatalogue(1, (parsed, parsed))
    reject(api, lambda: corrupt_catalogue.get("demo.power", 1))
