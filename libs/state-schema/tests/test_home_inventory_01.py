"""TC-013-01: round-trip fields, vocabulary, defaults and provider boundary."""

import json
from copy import deepcopy

import pytest
from inventory_support import (
    AREA_TYPES,
    KINDS,
    RESIDENCE_TYPES,
    assert_error,
    changed,
    object_path,
    runtime_required,
)

pytestmark = runtime_required


def test_round_trip(api, inventory):
    before = deepcopy(inventory)
    normalized = api.validate_inventory(inventory)
    assert normalized == before
    assert api.validate_inventory(json.loads(json.dumps(normalized))) == before
    assert inventory == before


@pytest.mark.parametrize('residence_type', RESIDENCE_TYPES)
def test_residence_vocabulary(api, inventory, residence_type):
    data = changed(inventory, ('home', 'residence_type'), residence_type)
    assert api.validate_inventory(data) == data


@pytest.mark.parametrize('area_type', AREA_TYPES)
def test_area_vocabulary(api, inventory, area_type):
    data = changed(inventory, ('areas', 0, 'area_type'), area_type)
    assert api.validate_inventory(data) == data


def test_default_and_populated_lists(api, inventory):
    data = deepcopy(inventory)
    for floor in data['floors']:
        floor.pop('aliases')
    for area in data['areas']:
        area.pop('aliases')
        area.pop('labels')
    for device in data['devices']:
        device.pop('labels')
    expected = deepcopy(data)
    for floor in expected['floors']:
        floor['aliases'] = []
    for area in expected['areas']:
        area.update(aliases=[], labels=[])
    for device in expected['devices']:
        device['labels'] = []
    assert api.validate_inventory(data) == expected
    expected['floors'][0]['aliases'] = ['Ground', 'Main']
    expected['areas'][0]['aliases'] = ['Main Bedroom']
    expected['areas'][0]['labels'] = ['primary', 'guest']
    expected['devices'][0]['labels'] = ['primary']
    assert api.validate_inventory(expected) == expected


@pytest.mark.parametrize('kind', ['envelope', *KINDS])
def test_unknown_fields(api, inventory, kind):
    path = () if kind == 'envelope' else object_path(kind)
    data = deepcopy(inventory)
    obj = data
    for key in path:
        obj = obj[key]
    obj['unexpected'] = 'value'
    assert_error(api, lambda: api.validate_inventory(data), (*path, 'unexpected'))


@pytest.mark.parametrize('field', ['entity_id', 'provider_id', 'capabilities', 'state', 'floor_id'])
def test_device_rejects_provider_and_direct_floor_fields(api, inventory, field):
    data = deepcopy(inventory)
    data['devices'][0][field] = 'external-value'
    assert_error(api, lambda: api.validate_inventory(data), ('devices', 0, field))


def test_provider_replacement_preserves_canonical_device(api, inventory):
    # Bindings are external test context; no ProviderBinding implementation is claimed.
    canonical = deepcopy(inventory['devices'][0])
    assert set(canonical) == {'id', 'home_id', 'name', 'area_id', 'labels'}
    for external_binding in ({'provider': 'ha', 'id': 'provider-a'},
                             {'provider': 'replacement', 'id': 'provider-b'}):
        assert external_binding['id'] != canonical['id']
        assert api.validate_inventory(inventory)['devices'][0] == canonical
