"""Strict version-1 inventory contracts and offline, side-effect-free selection.

The JSON-facing seam uses dictionaries; frozen domain records retain canonical
IDs and tuple-valued relationships. No provider identity or action API belongs
in this module. Constructors are typed records; ``Inventory.from_dict`` is the
validation boundary for external data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Callable, Literal, NoReturn, TypeVar, cast

ResidenceType = Literal['apartment', 'detached_house', 'townhouse', 'duplex', 'other']
AreaType = Literal[
    'living_room', 'dining_room', 'bedroom', 'kitchen', 'bathroom', 'laundry_room',
    'study', 'home_office', 'playroom', 'entrance', 'hallway', 'stairwell',
    'storage_room', 'garage', 'balcony', 'terrace', 'garden', 'other',
]
ErrorPath = tuple[str | int, ...]
RESIDENCE_TYPES = frozenset({'apartment', 'detached_house', 'townhouse', 'duplex', 'other'})
AREA_TYPES = frozenset({
    'living_room', 'dining_room', 'bedroom', 'kitchen', 'bathroom', 'laundry_room',
    'study', 'home_office', 'playroom', 'entrance', 'hallway', 'stairwell',
    'storage_room', 'garage', 'balcony', 'terrace', 'garden', 'other',
})
CANONICAL_ID_PATTERN = re.compile(r'[a-z][a-z0-9_-]{0,63}', re.ASCII)
T = TypeVar('T')


class InventoryError(ValueError):
    """Actionable validation/loader error with a deterministic structured path."""

    def __init__(self, path: ErrorPath, message: str, *, source: Path | None = None) -> None:
        self.path = path
        self.message = message
        location = '$' + ''.join(f'[{part}]' if isinstance(part, int) else f'.{part}'
                                 for part in path)
        prefix = f'{source}: ' if source is not None else ''
        super().__init__(f'{prefix}{location}: {message}')


def _object(value: object, path: ErrorPath, required: tuple[str, ...],
            optional: tuple[str, ...] = ()) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise InventoryError(path, 'expected an object with string field names')
    data = cast(dict[str, object], value)
    for key in required:
        if key not in data:
            raise InventoryError((*path, key), 'required field is missing')
    unknown = sorted(data.keys() - set(required) - set(optional))
    if unknown:
        raise InventoryError((*path, unknown[0]), 'unknown field')
    return data


def _text(value: object, path: ErrorPath, *, trimmed: bool = True) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InventoryError(path, 'expected a nonempty string')
    if trimmed and value != value.strip():
        raise InventoryError(path, 'must be trimmed; leading/trailing whitespace is not allowed')
    return value


def _id(value: object, path: ErrorPath) -> str:
    if not isinstance(value, str) or CANONICAL_ID_PATTERN.fullmatch(value) is None:
        raise InventoryError(path, 'expected a canonical ID matching ^[a-z][a-z0-9_-]{0,63}$')
    return value


def _nullable_id(value: object, path: ErrorPath) -> str | None:
    return None if value is None else _id(value, path)


def _integer(value: object, path: ErrorPath) -> int:
    if type(value) is not int:
        raise InventoryError(path, 'expected an integer, without coercion or booleans')
    return value


def _choice(value: object, path: ErrorPath, choices: frozenset[str]) -> str:
    text = _text(value, path)
    if text not in choices:
        expected = ', '.join(sorted(choices))
        raise InventoryError(path, f'unsupported value; expected one of {expected}')
    return text


def _records(value: object, path: ErrorPath,
             parse: Callable[[object, ErrorPath], T]) -> tuple[T, ...]:
    if not isinstance(value, list):
        raise InventoryError(path, 'expected a list')
    return tuple(parse(item, (*path, index)) for index, item in enumerate(value))


def _distinct(value: object, path: ErrorPath, parse: Callable[[object, ErrorPath], str],
              *, nonempty: bool = False) -> tuple[str, ...]:
    values = _records(value, path, parse)
    if nonempty and not values:
        raise InventoryError(path, 'must contain at least one member')
    seen: set[str] = set()
    for index, item in enumerate(values):
        if item in seen:
            raise InventoryError((*path, index), f'duplicate member: {item}')
        seen.add(item)
    return values


def _alias(value: object, path: ErrorPath) -> str:
    return _text(value, path, trimmed=False)


def _area_type(value: object, path: ErrorPath) -> str:
    return _choice(value, path, AREA_TYPES)


@dataclass(frozen=True, slots=True)
class Home:
    id: str
    name: str
    residence_type: ResidenceType

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Home:
        data = _object(value, path, ('id', 'name', 'residence_type'))
        return cls(_id(data['id'], (*path, 'id')), _text(data['name'], (*path, 'name')),
                   cast(ResidenceType, _choice(data['residence_type'],
                                              (*path, 'residence_type'), RESIDENCE_TYPES)))


@dataclass(frozen=True, slots=True)
class Floor:
    id: str
    home_id: str
    name: str
    level: int
    aliases: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Floor:
        data = _object(value, path, ('id', 'home_id', 'name', 'level'), ('aliases',))
        return cls(_id(data['id'], (*path, 'id')), _id(data['home_id'], (*path, 'home_id')),
                   _text(data['name'], (*path, 'name')), _integer(data['level'], (*path, 'level')),
                   _distinct(data.get('aliases', []), (*path, 'aliases'), _alias))


@dataclass(frozen=True, slots=True)
class Area:
    id: str
    home_id: str
    area_type: AreaType
    name: str
    floor_id: str | None
    labels: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Area:
        data = _object(value, path, ('id', 'home_id', 'area_type', 'name', 'floor_id'),
                       ('labels', 'aliases'))
        return cls(_id(data['id'], (*path, 'id')), _id(data['home_id'], (*path, 'home_id')),
                   cast(AreaType, _area_type(data['area_type'], (*path, 'area_type'))),
                   _text(data['name'], (*path, 'name')),
                   _nullable_id(data['floor_id'], (*path, 'floor_id')),
                   _distinct(data.get('labels', []), (*path, 'labels'), _id),
                   _distinct(data.get('aliases', []), (*path, 'aliases'), _alias))


@dataclass(frozen=True, slots=True)
class Device:
    id: str
    home_id: str
    name: str
    area_id: str | None
    labels: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Device:
        data = _object(value, path, ('id', 'home_id', 'name', 'area_id'), ('labels',))
        return cls(_id(data['id'], (*path, 'id')), _id(data['home_id'], (*path, 'home_id')),
                   _text(data['name'], (*path, 'name')),
                   _nullable_id(data['area_id'], (*path, 'area_id')),
                   _distinct(data.get('labels', []), (*path, 'labels'), _id))


@dataclass(frozen=True, slots=True)
class Label:
    id: str
    name: str

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> Label:
        data = _object(value, path, ('id', 'name'))
        return cls(_id(data['id'], (*path, 'id')), _text(data['name'], (*path, 'name')))


@dataclass(frozen=True, slots=True)
class AreaGroup:
    id: str
    name: str
    area_types: tuple[AreaType, ...]

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> AreaGroup:
        data = _object(value, path, ('id', 'name', 'area_types'))
        return cls(_id(data['id'], (*path, 'id')), _text(data['name'], (*path, 'name')),
                   cast(tuple[AreaType, ...], _distinct(data['area_types'], (*path, 'area_types'),
                                                       _area_type, nonempty=True)))


def _json_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class Inventory:
    schema_version: Literal[1]
    home: Home
    floors: tuple[Floor, ...]
    areas: tuple[Area, ...]
    devices: tuple[Device, ...]
    labels: tuple[Label, ...]
    area_groups: tuple[AreaGroup, ...]

    @classmethod
    def from_dict(cls, value: object) -> Inventory:
        data = _object(value, (), ('schema_version', 'home', 'floors', 'areas', 'devices',
                                  'labels', 'area_groups'))
        version = _integer(data['schema_version'], ('schema_version',))
        if version != 1:
            raise InventoryError(('schema_version',), f'unsupported schema version: {version}')
        result = cls(1, Home.from_dict(data['home'], ('home',)),
                     _records(data['floors'], ('floors',), Floor.from_dict),
                     _records(data['areas'], ('areas',), Area.from_dict),
                     _records(data['devices'], ('devices',), Device.from_dict),
                     _records(data['labels'], ('labels',), Label.from_dict),
                     _records(data['area_groups'], ('area_groups',), AreaGroup.from_dict))
        result._validate_references()
        return result

    def _validate_references(self) -> None:
        seen = {self.home.id}
        identity_groups: tuple[
            tuple[str, tuple[Floor | Area | Device | Label | AreaGroup, ...]], ...
        ] = (('floors', self.floors), ('areas', self.areas), ('devices', self.devices),
             ('labels', self.labels), ('area_groups', self.area_groups))
        for kind, records in identity_groups:
            for index, record in enumerate(records):
                if record.id in seen:
                    raise InventoryError((kind, index, 'id'),
                                         f'duplicate canonical ID: {record.id}')
                seen.add(record.id)
        floor_ids = {floor.id for floor in self.floors}
        area_ids = {area.id for area in self.areas}
        label_ids = {label.id for label in self.labels}
        containment_groups: tuple[tuple[str, tuple[Floor | Area | Device, ...]], ...] = (
            ('floors', self.floors), ('areas', self.areas), ('devices', self.devices),
        )
        for kind, contained in containment_groups:
            for index, contained_record in enumerate(contained):
                if contained_record.home_id != self.home.id:
                    raise InventoryError((kind, index, 'home_id'),
                                         'must reference this inventory Home')
        for index, area in enumerate(self.areas):
            if area.floor_id is not None and area.floor_id not in floor_ids:
                raise InventoryError(('areas', index, 'floor_id'), 'unknown Floor ID in this Home')
        for index, device in enumerate(self.devices):
            if device.area_id is not None and device.area_id not in area_ids:
                raise InventoryError(('devices', index, 'area_id'), 'unknown Area ID in this Home')
        label_groups: tuple[tuple[str, tuple[Area | Device, ...]], ...] = (
            ('areas', self.areas), ('devices', self.devices),
        )
        for kind, labeled in label_groups:
            for index, labeled_record in enumerate(labeled):
                for label_index, label_id in enumerate(labeled_record.labels):
                    if label_id not in label_ids:
                        raise InventoryError((kind, index, 'labels', label_index),
                                             f'unknown registered Label ID: {label_id}')

    def to_dict(self) -> dict[str, object]:
        """Return a detached JSON-compatible snapshot; editing it cannot alter IDs here."""
        return cast(dict[str, object], _json_value(self))



def safe_inventory_path(path: ErrorPath) -> ErrorPath:
    """Retain schema fields/indices for wrappers, redact arbitrary submitted keys.

    Inventory's own diagnostics retain its legacy path convention. Wrappers
    with value-free error contracts use this schema-derived safe vocabulary.
    """
    allowed = {field.name for model in (Inventory, Home, Floor, Area, Device, Label, AreaGroup)
               for field in fields(model)}
    return tuple(part if isinstance(part, int) or part in allowed else '<unknown>'
                 for part in path)


def validate_inventory(data: object) -> dict[str, object]:
    """Validate external JSON data and normalize optional lists without mutation."""
    return Inventory.from_dict(data).to_dict()


@dataclass(frozen=True, slots=True)
class _ObjectPairs:
    members: list[tuple[str, object]]


def _decoded_json(value: object, path: ErrorPath = ()) -> object:
    # Preserve object pairs until this pass so duplicate fields cannot silently
    # overwrite a previously supplied value, including in nested objects.
    if isinstance(value, _ObjectPairs):
        result: dict[str, object] = {}
        for key, item in value.members:
            if key in result:
                raise InventoryError((*path, key), 'duplicate JSON field')
            result[key] = _decoded_json(item, (*path, key))
        return result
    if isinstance(value, list):
        return [_decoded_json(item, (*path, index)) for index, item in enumerate(value)]
    return value


def _reject_constant(token: str) -> NoReturn:
    raise InventoryError((), f'nonstandard JSON constant: {token}')


def load_inventory(path: str | Path) -> dict[str, object]:
    """Read an explicit UTF-8 JSON inventory offline, preserving the source file."""
    source = Path(path)
    try:
        text = source.read_text(encoding='utf-8')
        data = json.loads(text, object_pairs_hook=_ObjectPairs, parse_constant=_reject_constant)
        return validate_inventory(_decoded_json(data))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InventoryError((), str(error), source=source) from error
    except InventoryError as error:
        raise InventoryError(error.path, error.message, source=source) from error


def resolve_targets(inventory: object, *, home_id: object,
                    selector: object) -> dict[str, list[str]]:
    """Resolve explicitly selected areas/devices, with no action or provider calls."""
    model = Inventory.from_dict(inventory)
    requested_home = _id(home_id, ('home_id',))
    if requested_home != model.home.id:
        raise InventoryError(('home_id',), 'must select this inventory Home')
    data = _object(selector, ('selector',), (), ('area_ids', 'area_group_ids', 'label_ids'))
    forms = [key for key in ('area_ids', 'area_group_ids') if key in data]
    if len(forms) != 1:
        raise InventoryError(('selector',), 'provide exactly one of area_ids or area_group_ids')
    form = forms[0]
    selected = _distinct(data[form], ('selector', form), _id, nonempty=True)
    requested_labels = _distinct(data.get('label_ids', []), ('selector', 'label_ids'), _id)
    known_ids = ({area.id for area in model.areas} if form == 'area_ids'
                 else {group.id for group in model.area_groups})
    for index, target in enumerate(selected):
        if target not in known_ids:
            raise InventoryError(('selector', form, index),
                                 f'unknown target ID in this Home: {target}')
    known_labels = {label.id for label in model.labels}
    for index, label in enumerate(requested_labels):
        if label not in known_labels:
            raise InventoryError(('selector', 'label_ids', index),
                                 f'unknown registered Label: {label}')
    if form == 'area_ids':
        selected_areas = set(selected)
    else:
        room_types = {area_type for group in model.area_groups if group.id in selected
                      for area_type in group.area_types}
        selected_areas = {area.id for area in model.areas if area.area_type in room_types}
    label_filter = set(requested_labels)
    selected_areas = {area.id for area in model.areas if area.id in selected_areas
                      and label_filter.issubset(area.labels)}
    devices = {device.id for device in model.devices if device.area_id in selected_areas}
    return {'area_ids': sorted(selected_areas), 'device_ids': sorted(devices)}


def main(argv: list[str] | None = None) -> int:
    """Validate an explicit file path and emit normalized JSON or actionable stderr."""
    parser = argparse.ArgumentParser(description='Validate a local home inventory (offline).')
    parser.add_argument('path', type=Path, help='UTF-8 version-1 inventory JSON file')
    args = parser.parse_args(argv)
    try:
        inventory = load_inventory(args.path)
    except InventoryError as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps(inventory, ensure_ascii=True, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
