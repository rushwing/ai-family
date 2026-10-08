"""TC-013-02: identity-preserving edits and nullable containment."""

from copy import deepcopy

import pytest
from inventory_support import KINDS, assert_targets, object_path, resolve, runtime_required

pytestmark = runtime_required


@pytest.mark.parametrize('level', [-12, -1, 0, 1, 27])
def test_floor_levels_are_integers_not_fixed_enumeration(api, inventory, level):
    inventory['floors'][0].update(level=level, name='Independently named floor')
    assert api.validate_inventory(inventory) == inventory


def test_all_display_names_can_change_without_changing_identity(api, inventory):
    before = deepcopy(inventory)
    for kind in KINDS:
        obj = inventory
        for key in object_path(kind):
            obj = obj[key]
        obj['name'] = 'Editable display name'
    inventory['areas'][1]['name'] = inventory['areas'][0]['name']
    inventory['devices'][1]['name'] = inventory['devices'][0]['name']
    validated = api.validate_inventory(inventory)
    for kind in KINDS:
        records = [validated[kind]] if kind == 'home' else validated[kind]
        original = [before[kind]] if kind == 'home' else before[kind]
        for record, old in zip(records, original, strict=True):
            assert record['id'] == old['id']
            for ref in ('home_id', 'floor_id', 'area_id', 'labels', 'area_types'):
                if ref in old:
                    assert record[ref] == old[ref]
    assert_targets(resolve(api, validated, {'area_ids': ['area-bedroom-01']}),
                   ['area-bedroom-01'], ['device-bedroom-light-01'])
    assert_targets(resolve(api, validated, {'area_group_ids': ['resting'],
                                          'label_ids': ['primary']}),
                   ['area-bedroom-01'], ['device-bedroom-light-01'])


@pytest.mark.parametrize('floor_id', ['floor-upper', None])
@pytest.mark.parametrize('area_id', ['area-bedroom-02', None])
def test_moving_and_unassigning_preserves_ids_and_selection(api, inventory, floor_id, area_id):
    inventory['floors'].append({'id': 'floor-upper', 'home_id': 'home-example',
                                'name': 'Upper', 'level': 1, 'aliases': []})
    inventory['areas'][1]['floor_id'] = floor_id
    inventory['devices'][0]['area_id'] = area_id
    validated = api.validate_inventory(inventory)
    assert validated == inventory
    device = validated['devices'][0]
    assert device['id'] == 'device-bedroom-light-01'
    area = next((a for a in validated['areas'] if a['id'] == device['area_id']), None)
    assert (area['floor_id'] if area else None) == (floor_id if area_id else None)
    assert 'floor_id' not in device
    expected = ['device-bedroom-light-02']
    if area_id:
        expected.append('device-bedroom-light-01')
    assert_targets(resolve(api, validated, {'area_ids': ['area-bedroom-02']}),
                   ['area-bedroom-02'], expected)


def test_groups_are_editable_inventory_data(api, inventory):
    inventory['area_groups'] = [
        {'id': 'custom', 'name': 'Custom rooms', 'area_types': ['bedroom', 'balcony']},
        {'id': 'unused', 'name': 'Unused group', 'area_types': ['garage']},
    ]
    validated = api.validate_inventory(inventory)
    assert_targets(resolve(api, validated, {'area_group_ids': ['custom']}),
                   ['area-bedroom-01', 'area-bedroom-02', 'area-bedroom-03', 'area-balcony'],
                   [f'device-bedroom-light-{i:02}' for i in range(1, 4)])
    assert_targets(resolve(api, validated, {'area_group_ids': ['unused']}), [], [])
    inventory['area_groups'][0].update(name='Renamed group', area_types=['living_room'])
    assert_targets(resolve(api, api.validate_inventory(inventory), {'area_group_ids': ['custom']}),
                   ['area-living-room'], [])
