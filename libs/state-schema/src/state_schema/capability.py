"""REQ-016: strict offline Capability descriptors and bounded payload schemas.

Factories are external boundaries. Direct constructors are internal typed
records. Metadata describes evidence requirements; nothing dispatches actions,
allocates task state or interprets ACK as an observation.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import cast

ErrorPath = tuple[str | int, ...]
Scalar = bool | int | float | str | None
Constraint = Scalar | tuple[Scalar, ...]
_MEMBER = re.compile(r"[a-z][a-z0-9_]{0,63}", re.ASCII)
_ID = re.compile(r"[a-z][a-z0-9_]{0,31}(\.[a-z][a-z0-9_]{0,31}){1,3}", re.ASCII)
_TYPES = ("boolean", "integer", "number", "string", "null", "object", "array")
_SCALARS = ("boolean", "integer", "number", "string", "null")


class CapabilityError(ValueError):
    """Deterministic location/reason without submitted values or arbitrary keys."""

    def __init__(self, path: ErrorPath, message: str) -> None:
        self.path = path
        self.message = message
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in path
        )
        super().__init__(f"{location}: {message}")


def _map(value: object, path: ErrorPath) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise CapabilityError(path, "expected an object with string field names")
    return cast(dict[str, object], value)


def _fields(
    data: dict[str, object],
    path: ErrorPath,
    required: tuple[str, ...],
    optional: tuple[str, ...] = (),
) -> None:
    for key in required:
        if key not in data:
            raise CapabilityError((*path, key), "required field is missing")
    if data.keys() - set(required) - set(optional):
        raise CapabilityError((*path, "<unknown>"), "unknown structural field")


def _object(value: object, path: ErrorPath, fields: tuple[str, ...]) -> dict[str, object]:
    data = _map(value, path)
    _fields(data, path, fields)
    return data


def _integer(value: object, path: ErrorPath, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise CapabilityError(path, "expected an integer within the declared bounds")
    return value


def _number(value: object, path: ErrorPath) -> int | float:
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        raise CapabilityError(path, "expected a finite number excluding booleans")
    return cast(int | float, value)


def _text(value: object, path: ErrorPath, limit: int) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise CapabilityError(path, "expected nonblank text within the declared limit")
    return value


def _name(value: object, path: ErrorPath, *, identity: bool = False) -> str:
    pattern = _ID if identity else _MEMBER
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise CapabilityError(path, "invalid canonical name")
    return value


def _members(value: object, path: ErrorPath) -> dict[str, object]:
    data = _map(value, path)
    if any(_MEMBER.fullmatch(key) is None for key in data):
        raise CapabilityError((*path, "<property>"), "invalid canonical member name")
    return data


def _choice(value: object, path: ErrorPath, choices: tuple[str, ...]) -> str:
    if type(value) is not str or value not in choices:
        raise CapabilityError(path, "unsupported contract value")
    return value


def _equal(left: object, right: object) -> bool:
    """Structural equality: unordered object keys, ordered lists, typed scalars."""
    if type(left) in (int, float) and type(right) in (int, float):
        return bool(left == right)
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal(v, right[k]) for k, v in left.items())
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    return bool(left == right)


def _json_snapshot(
    value: object, path: ErrorPath, depth: int = 1, active: frozenset[int] = frozenset()
) -> object:
    if depth > 16:
        raise CapabilityError(path, "payload depth exceeds 16")
    if type(value) in (str, bool, int) or value is None:
        return value
    if type(value) is float:
        return _number(value, path)
    if type(value) not in (dict, list):
        raise CapabilityError(path, "expected a strict JSON value")
    if id(value) in active:
        raise CapabilityError(path, "cyclic JSON value")
    active = active | {id(value)}
    if type(value) is list:
        return [
            _json_snapshot(item, (*path, i), depth + 1, active)
            for i, item in enumerate(cast(list[object], value))
        ]
    data = _map(value, path)
    return {
        key: _json_snapshot(item, (*path, "<property>"), depth + 1, active)
        for key, item in data.items()
    }


@dataclass(frozen=True, slots=True)
class Schema:
    kind: str
    properties: tuple[tuple[str, Schema], ...] = ()
    required: tuple[str, ...] = ()
    items: Schema | None = None
    constraints: tuple[tuple[str, Constraint], ...] = ()

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Schema:
        return _schema(value, path, 1, frozenset())

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"type": self.kind}
        if self.kind == "object":
            result.update(
                properties={key: item.to_dict() for key, item in self.properties},
                required=list(self.required),
                additionalProperties=False,
            )
        if self.kind == "array":
            result["items"] = None if self.items is None else self.items.to_dict()
        for key, value in self.constraints:
            result[key] = list(value) if isinstance(value, tuple) else value
        return result

    def validate(self, payload: object) -> object:
        schema = Schema.from_dict(self.to_dict())
        result = _json_snapshot(payload, ())
        _instance(schema, result, ())
        return result


def _schema(value: object, path: ErrorPath, depth: int, active: frozenset[int]) -> Schema:
    if depth > 16:
        raise CapabilityError(path, "schema depth exceeds 16")
    if id(value) in active:
        raise CapabilityError(path, "cyclic schema")
    data = _map(value, path)
    active = active | {id(value)}
    if "type" not in data:
        raise CapabilityError((*path, "type"), "required field is missing")
    kind = _choice(data["type"], (*path, "type"), _TYPES)
    properties: tuple[tuple[str, Schema], ...] = ()
    required: tuple[str, ...] = ()
    items = None
    if kind == "object":
        _fields(data, path, ("type", "properties", "required", "additionalProperties"))
        if data["additionalProperties"] is not False:
            raise CapabilityError((*path, "additionalProperties"), "must be literal false")
        members = _members(data["properties"], (*path, "properties"))
        properties = tuple(
            (key, _schema(item, (*path, "properties", key), depth + 1, active))
            for key, item in members.items()
        )
        raw_required = data["required"]
        if type(raw_required) is not list:
            raise CapabilityError((*path, "required"), "expected a list of declared member names")
        names: list[str] = []
        for i, name in enumerate(raw_required):
            if type(name) is not str or name not in members or name in names:
                raise CapabilityError((*path, "required", i), "expected distinct declared names")
            names.append(name)
        required = tuple(names)
        allowed: tuple[str, ...] = ()
    elif kind == "array":
        allowed = ("minItems", "maxItems")
        _fields(data, path, ("type", "items"), allowed)
        items = _schema(data["items"], (*path, "items"), depth + 1, active)
    else:
        allowed = ("enum",)
        if kind in ("integer", "number"):
            allowed += ("minimum", "maximum")
        elif kind == "string":
            allowed += ("minLength", "maxLength")
        _fields(data, path, ("type",), allowed)
    constraints: list[tuple[str, Constraint]] = []
    for key in allowed:
        if key == "enum" or key not in data:
            continue
        if key in ("minimum", "maximum"):
            bound: Scalar = _number(data[key], (*path, key))
            if kind == "integer" and type(bound) is not int:
                raise CapabilityError((*path, key), "integer schema requires integer bounds")
        else:
            bound = _integer(data[key], (*path, key))
        constraints.append((key, bound))
    values = dict(constraints)
    for lower, upper in (
        ("minimum", "maximum"),
        ("minLength", "maxLength"),
        ("minItems", "maxItems"),
    ):
        if lower in values and upper in values:
            if cast(int | float, values[lower]) > cast(int | float, values[upper]):
                raise CapabilityError((*path, upper), "upper bound is less than lower bound")
    schema = Schema(kind, properties, required, items, tuple(constraints))
    if "enum" in data:
        raw = data["enum"]
        if type(raw) is not list or not raw:
            raise CapabilityError((*path, "enum"), "expected a nonempty scalar list")
        enums: list[Scalar] = []
        for i, candidate in enumerate(raw):
            if type(candidate) not in (bool, int, float, str) and candidate is not None:
                raise CapabilityError((*path, "enum", i), "expected a scalar")
            _instance(schema, candidate, (*path, "enum", i))
            if any(_equal(candidate, existing) for existing in enums):
                raise CapabilityError((*path, "enum", i), "duplicate enum value")
            enums.append(cast(Scalar, candidate))
        schema = Schema(
            kind, properties, required, items, (*schema.constraints, ("enum", tuple(enums)))
        )
    return schema


def _instance(schema: Schema, value: object, path: ErrorPath) -> None:
    kind = schema.kind
    if kind == "boolean":
        if type(value) is not bool:
            raise CapabilityError(path, "expected a boolean")
    elif kind == "integer":
        if type(value) is not int:
            raise CapabilityError(path, "expected an integer excluding booleans")
    elif kind == "number":
        _number(value, path)
    elif kind == "string":
        if type(value) is not str:
            raise CapabilityError(path, "expected a string")
    elif kind == "null":
        if value is not None:
            raise CapabilityError(path, "expected null")
    elif kind == "object":
        data = _map(value, path)
        _fields(data, path, schema.required, tuple(key for key, _ in schema.properties))
        for key, item in schema.properties:
            if key in data:
                _instance(item, data[key], (*path, key))
    elif kind == "array":
        if type(value) is not list:
            raise CapabilityError(path, "expected an array")
        if schema.items is None:
            raise CapabilityError(path, "array schema has no items")
        for i, item in enumerate(value):
            _instance(schema.items, item, (*path, i))
    for key, limit in schema.constraints:
        if key == "enum":
            if not any(_equal(value, item) for item in cast(tuple[Scalar, ...], limit)):
                raise CapabilityError(path, "value is not a declared enum member")
        elif key in ("minimum", "maximum"):
            number = cast(int | float, value)
            bound = cast(int | float, limit)
            if (key == "minimum" and number < bound) or (key == "maximum" and number > bound):
                raise CapabilityError(path, "value is outside numeric bounds")
        else:
            size = len(cast(str | list[object], value))
            bound_int = cast(int, limit)
            if (key.startswith("min") and size < bound_int) or (
                key.startswith("max") and size > bound_int
            ):
                raise CapabilityError(path, "value is outside length bounds")


@dataclass(frozen=True, slots=True)
class TargetSource:
    source: str
    field: str | None = None
    value: Scalar = None

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> TargetSource:
        data = _map(value, path)
        source = _choice(data.get("source"), (*path, "source"), ("input", "constant"))
        if source == "input":
            _fields(data, path, ("source", "field"))
            return cls(source, _name(data["field"], (*path, "field")))
        _fields(data, path, ("source", "value"))
        scalar = data["value"]
        if type(scalar) not in (bool, int, float, str):
            raise CapabilityError((*path, "value"), "expected a State scalar")
        if type(scalar) is float:
            _number(scalar, (*path, "value"))
        return cls(source, value=cast(Scalar, scalar))

    def to_dict(self) -> dict[str, object]:
        return (
            {"source": self.source, "field": self.field}
            if self.source == "input"
            else {"source": self.source, "value": self.value}
        )


@dataclass(frozen=True, slots=True)
class CompletionPolicy:
    kind: str
    event: str | None = None
    targets: tuple[tuple[str, TargetSource], ...] = ()

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> CompletionPolicy:
        data = _map(value, path)
        kind = _choice(
            data.get("kind"), (*path, "kind"), ("ack_only", "event_confirmed", "state_converged")
        )
        if kind == "ack_only":
            _fields(data, path, ("kind",))
            return cls(kind)
        if kind == "event_confirmed":
            _fields(data, path, ("kind", "event"))
            return cls(kind, event=_name(data["event"], (*path, "event")))
        _fields(data, path, ("kind", "targets"))
        targets = _members(data["targets"], (*path, "targets"))
        if not targets:
            raise CapabilityError((*path, "targets"), "expected nonempty targets")
        return cls(
            kind,
            targets=tuple(
                (name, TargetSource.from_dict(item, (*path, "targets", name)))
                for name, item in targets.items()
            ),
        )

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"kind": self.kind}
        if self.kind == "event_confirmed":
            result["event"] = self.event
        elif self.kind == "state_converged":
            result["targets"] = {key: item.to_dict() for key, item in self.targets}
        return result


@dataclass(frozen=True, slots=True)
class Property:
    title: str
    description: str
    value_schema: Schema
    read_only: bool

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Property:
        data = _object(value, path, ("title", "description", "value_schema", "read_only"))
        schema = Schema.from_dict(data["value_schema"], (*path, "value_schema"))
        if schema.kind not in ("boolean", "integer", "number", "string"):
            raise CapabilityError(
                (*path, "value_schema", "type"), "property requires a State scalar"
            )
        if type(data["read_only"]) is not bool:
            raise CapabilityError((*path, "read_only"), "expected a boolean")
        return cls(
            _text(data["title"], (*path, "title"), 256),
            _text(data["description"], (*path, "description"), 2048),
            schema,
            data["read_only"],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "description": self.description,
            "value_schema": self.value_schema.to_dict(),
            "read_only": self.read_only,
        }


@dataclass(frozen=True, slots=True)
class Event:
    title: str
    description: str
    data_schema: Schema

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Event:
        data = _object(value, path, ("title", "description", "data_schema"))
        return cls(
            _text(data["title"], (*path, "title"), 256),
            _text(data["description"], (*path, "description"), 2048),
            Schema.from_dict(data["data_schema"], (*path, "data_schema")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "description": self.description,
            "data_schema": self.data_schema.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Action:
    title: str
    description: str
    input_schema: Schema
    output_schema: Schema
    risk: str
    timeout_ms: int
    idempotency: str
    completion_policy: CompletionPolicy

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Action:
        data = _object(
            value,
            path,
            (
                "title",
                "description",
                "input_schema",
                "output_schema",
                "risk",
                "timeout_ms",
                "idempotency",
                "completion_policy",
            ),
        )
        input_schema = Schema.from_dict(data["input_schema"], (*path, "input_schema"))
        if input_schema.kind != "object":
            raise CapabilityError(
                (*path, "input_schema", "type"), "action input requires an object"
            )
        return cls(
            _text(data["title"], (*path, "title"), 256),
            _text(data["description"], (*path, "description"), 2048),
            input_schema,
            Schema.from_dict(data["output_schema"], (*path, "output_schema")),
            _choice(data["risk"], (*path, "risk"), ("low", "medium", "high")),
            _integer(data["timeout_ms"], (*path, "timeout_ms"), 1, 86400000),
            _choice(
                data["idempotency"],
                (*path, "idempotency"),
                ("safe_repeat", "key_required", "non_idempotent"),
            ),
            CompletionPolicy.from_dict(data["completion_policy"], (*path, "completion_policy")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "description": self.description,
            "input_schema": self.input_schema.to_dict(),
            "output_schema": self.output_schema.to_dict(),
            "risk": self.risk,
            "timeout_ms": self.timeout_ms,
            "idempotency": self.idempotency,
            "completion_policy": self.completion_policy.to_dict(),
        }


def _references(
    action: Action, properties: dict[str, Property], events: dict[str, Event], path: ErrorPath
) -> None:
    policy = action.completion_policy
    path = (*path, "completion_policy")
    if policy.kind == "event_confirmed" and policy.event not in events:
        raise CapabilityError((*path, "event"), "event is not declared")
    inputs = dict(action.input_schema.properties)
    for name, target in policy.targets:
        target_path = (*path, "targets", name if name in properties else "<unknown>")
        if name not in properties or properties[name].read_only:
            raise CapabilityError(target_path, "target requires a declared writable property")
        prop = properties[name]
        if target.source == "constant":
            _instance(prop.value_schema, target.value, (*target_path, "value"))
        elif target.field not in action.input_schema.required or target.field not in inputs:
            raise CapabilityError(
                (*target_path, "field"), "input must be a required declared field"
            )
        elif not _equal(inputs[target.field].to_dict(), prop.value_schema.to_dict()):
            raise CapabilityError(
                (*target_path, "field"), "input and property schemas must be equal"
            )


@dataclass(frozen=True, slots=True)
class CapabilityDescriptor:
    schema_version: int
    capability_id: str
    capability_version: int
    title: str
    description: str
    properties: tuple[tuple[str, Property], ...]
    actions: tuple[tuple[str, Action], ...]
    events: tuple[tuple[str, Event], ...]

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> CapabilityDescriptor:
        data = _object(
            value,
            path,
            (
                "schema_version",
                "capability_id",
                "capability_version",
                "title",
                "description",
                "properties",
                "actions",
                "events",
            ),
        )
        version = _integer(data["schema_version"], (*path, "schema_version"), 1, 1)
        identity = _name(data["capability_id"], (*path, "capability_id"), identity=True)
        revision = _integer(data["capability_version"], (*path, "capability_version"), 1)
        properties = tuple(
            (key, Property.from_dict(item, (*path, "properties", key)))
            for key, item in _members(data["properties"], (*path, "properties")).items()
        )
        actions = tuple(
            (key, Action.from_dict(item, (*path, "actions", key)))
            for key, item in _members(data["actions"], (*path, "actions")).items()
        )
        events = tuple(
            (key, Event.from_dict(item, (*path, "events", key)))
            for key, item in _members(data["events"], (*path, "events")).items()
        )
        if not (properties or actions or events):
            raise CapabilityError(path, "descriptor requires at least one interaction")
        for name, action in actions:
            _references(action, dict(properties), dict(events), (*path, "actions", name))
        return cls(
            version,
            identity,
            revision,
            _text(data["title"], (*path, "title"), 256),
            _text(data["description"], (*path, "description"), 2048),
            properties,
            actions,
            events,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "title": self.title,
            "description": self.description,
            "properties": {key: item.to_dict() for key, item in self.properties},
            "actions": {key: item.to_dict() for key, item in self.actions},
            "events": {key: item.to_dict() for key, item in self.events},
        }

    def validate_payload(self, kind: object, name: object, payload: object) -> object:
        parsed = CapabilityDescriptor.from_dict(self.to_dict())
        interaction = _choice(
            kind, ("kind",), ("property", "action_input", "action_output", "event")
        )
        member = _name(name, ("<property>",))
        properties, actions, events = (
            dict(parsed.properties),
            dict(parsed.actions),
            dict(parsed.events),
        )
        if interaction == "property" and member in properties:
            schema = properties[member].value_schema
        elif interaction == "event" and member in events:
            schema = events[member].data_schema
        elif interaction in ("action_input", "action_output") and member in actions:
            action = actions[member]
            schema = action.input_schema if interaction == "action_input" else action.output_schema
        else:
            raise CapabilityError(("<unknown>",), "interaction is not declared")
        return schema.validate(payload)


@dataclass(frozen=True, slots=True)
class CapabilityCatalogue:
    schema_version: int
    capabilities: tuple[CapabilityDescriptor, ...]

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> CapabilityCatalogue:
        data = _object(value, path, ("schema_version", "capabilities"))
        version = _integer(data["schema_version"], (*path, "schema_version"), 1, 1)
        raw = data["capabilities"]
        if type(raw) is not list:
            raise CapabilityError((*path, "capabilities"), "expected an array")
        items: list[CapabilityDescriptor] = []
        seen: set[tuple[str, int]] = set()
        for i, item in enumerate(raw):
            parsed = CapabilityDescriptor.from_dict(item, (*path, "capabilities", i))
            pair = (parsed.capability_id, parsed.capability_version)
            if pair in seen:
                raise CapabilityError(
                    (*path, "capabilities", i), "duplicate identity/revision pair"
                )
            seen.add(pair)
            items.append(parsed)
        return cls(version, tuple(items))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capabilities": [item.to_dict() for item in self.capabilities],
        }

    def get(self, capability_id: object, capability_version: object) -> CapabilityDescriptor:
        parsed = CapabilityCatalogue.from_dict(self.to_dict())
        identity = _name(capability_id, ("capability_id",), identity=True)
        revision = _integer(capability_version, ("capability_version",), 1)
        for item in parsed.capabilities:
            if (item.capability_id, item.capability_version) == (identity, revision):
                return item
        raise CapabilityError((), "exact capability identity/revision is not declared")

    def validate_payload(
        self,
        capability_id: object,
        capability_version: object,
        kind: object,
        name: object,
        payload: object,
    ) -> object:
        return self.get(capability_id, capability_version).validate_payload(kind, name, payload)


def validate_schema(data: object) -> dict[str, object]:
    return Schema.from_dict(data).to_dict()


def validate_payload(schema: object, payload: object) -> object:
    return Schema.from_dict(schema).validate(payload)


def validate_capability(data: object) -> dict[str, object]:
    return CapabilityDescriptor.from_dict(data).to_dict()


def validate_capabilities(data: object) -> dict[str, object]:
    return CapabilityCatalogue.from_dict(data).to_dict()


def _decode(text: object) -> object:
    if type(text) is not str:
        raise CapabilityError((), "expected JSON text")

    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise CapabilityError(("<unknown>",), "duplicate JSON object key")
            result[key] = value
        return result

    def constant(value: str) -> object:
        raise CapabilityError((), "nonfinite JSON constant is not allowed")

    try:
        return cast(object, json.loads(text, object_pairs_hook=pairs, parse_constant=constant))
    except CapabilityError:
        raise
    except (ValueError, RecursionError):
        raise CapabilityError((), "invalid JSON text") from None


def load_capability_json(text: object) -> CapabilityDescriptor:
    """Parse strict text without file I/O; already-parsed dicts cannot retain duplicate keys."""
    return CapabilityDescriptor.from_dict(_decode(text))


def load_capabilities_json(text: object) -> CapabilityCatalogue:
    return CapabilityCatalogue.from_dict(_decode(text))
