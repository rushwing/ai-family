"""Test-side contract data and assertions, never an inventory implementation."""

from copy import deepcopy
from importlib.util import find_spec
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / 'docs/product/home-intelligence/examples/three-bedroom-apartment.example.json'
CLI = ('-m', 'state_schema.home_inventory')
RUNTIME_AVAILABLE = (
    find_spec('state_schema') is not None
    and find_spec('state_schema.home_inventory') is not None
)
runtime_required = pytest.mark.skipif(
    not RUNTIME_AVAILABLE,
    reason='REQ-013 runtime state_schema.home_inventory is not implemented; acceptance pending',
)
PRESETS = {
    'daily_life': ['living_room', 'dining_room'],
    'resting': ['bedroom'],
    'kitchen_bath': ['kitchen', 'bathroom', 'laundry_room'],
    'studio': ['study', 'home_office', 'playroom'],
    'traffic': ['entrance', 'hallway', 'stairwell'],
    'storage_utility': ['storage_room', 'garage'],
    'outdoor_spaces': ['balcony', 'terrace', 'garden'],
}
AREA_TYPES = sorted({t for types in PRESETS.values() for t in types} | {'other'})
RESIDENCE_TYPES = ['apartment', 'detached_house', 'townhouse', 'duplex', 'other']
KINDS = ['home', 'floors', 'areas', 'devices', 'labels', 'area_groups']
ROOMS = [f'area-bedroom-{i:02}' for i in range(1, 4)]
LIGHTS = [f'device-bedroom-light-{i:02}' for i in range(1, 4)]


def at(data, path):
    for key in path:
        data = data[key]
    return data


def changed(data, path, value):
    result = deepcopy(data)
    at(result, path[:-1])[path[-1]] = value
    return result


def object_path(kind):
    return ('home',) if kind == 'home' else (kind, 0)


def assert_error(api, call, expected_path):
    """Check the structured location twice without freezing library-specific prose."""
    paths = []
    for _ in range(2):
        with pytest.raises(api.InventoryError) as caught:
            call()
        path = caught.value.path
        assert isinstance(path, (tuple, list))
        assert tuple(path) == tuple(expected_path)
        assert str(caught.value).strip(), 'Errors need a human-readable explanation'
        paths.append(tuple(path))
    assert paths[0] == paths[1]


def resolve(api, inventory, selector, home_id='home-example'):
    return api.resolve_targets(inventory, home_id=home_id, selector=selector)


def assert_targets(result, areas, devices):
    assert result == {'area_ids': sorted(areas), 'device_ids': sorted(devices)}
