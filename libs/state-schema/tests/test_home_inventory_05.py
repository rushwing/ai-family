"""TC-013-05: exact target sets, intersections and permutation invariance."""

from copy import deepcopy

import pytest
from inventory_support import LIGHTS, ROOMS, assert_targets, resolve, runtime_required

pytestmark = runtime_required


@pytest.mark.parametrize('selector,areas,devices', [
    ({'area_ids': ['area-bedroom-02']}, ['area-bedroom-02'], ['device-bedroom-light-02']),
    ({'area_ids': ['area-living-room']}, ['area-living-room'], []),
    ({'area_group_ids': ['resting']}, ROOMS, LIGHTS),
    ({'area_group_ids': ['resting'], 'label_ids': ['children']},
     ['area-bedroom-02'], ['device-bedroom-light-02']),
    ({'area_group_ids': ['daily_life', 'resting']},
     [*ROOMS, 'area-living-room', 'area-dining-room'], LIGHTS),
    ({'area_group_ids': ['studio']}, [], []),
    ({'area_group_ids': ['storage_utility']}, [], []),
    ({'area_group_ids': ['resting'], 'label_ids': ['outdoor']}, [], []),
    ({'area_group_ids': ['resting'], 'label_ids': []}, ROOMS, LIGHTS),
])
def test_exact_results(api, inventory, selector, areas, devices):
    assert_targets(resolve(api, api.validate_inventory(inventory), selector), areas, devices)


def test_overlapping_groups_and_input_permutations(api, inventory):
    inventory['area_groups'].append({'id': 'overlap', 'name': 'Overlap',
                                     'area_types': ['bedroom', 'living_room']})
    selector = {'area_group_ids': ['resting', 'overlap']}
    expected_areas = [*ROOMS, 'area-living-room']
    for reverse in (False, True):
        data = deepcopy(inventory)
        if reverse:
            for key in ('floors', 'areas', 'devices', 'labels', 'area_groups'):
                data[key].reverse()
            selector['area_group_ids'].reverse()
        assert_targets(resolve(api, api.validate_inventory(data), selector), expected_areas, LIGHTS)


def test_label_intersection_uses_areas_not_devices(api, inventory):
    inventory['areas'][1]['labels'] = ['children', 'primary']
    inventory['devices'][0]['labels'] = ['children', 'primary']
    selector = {'area_group_ids': ['resting'], 'label_ids': ['children', 'primary']}
    assert_targets(resolve(api, api.validate_inventory(inventory), selector),
                   ['area-bedroom-02'], ['device-bedroom-light-02'])
    selector['label_ids'].reverse()
    assert_targets(resolve(api, api.validate_inventory(inventory), selector),
                   ['area-bedroom-02'], ['device-bedroom-light-02'])


def test_unassigned_device_excluded_and_unassigned_floor_selectable(api, inventory):
    inventory['devices'][0]['area_id'] = None
    inventory['areas'][0]['floor_id'] = None
    assert_targets(resolve(api, api.validate_inventory(inventory), {'area_ids': [ROOMS[0]]}),
                   [ROOMS[0]], [])


def test_explicit_area_order_and_multiple_devices(api, inventory):
    inventory['devices'].append({'id': 'additional-light', 'home_id': 'home-example',
                                 'name': 'Additional light', 'area_id': ROOMS[0], 'labels': []})
    for area_ids in ([ROOMS[1], ROOMS[0]], [ROOMS[0], ROOMS[1]]):
        assert_targets(resolve(api, api.validate_inventory(inventory), {'area_ids': area_ids}),
                       ROOMS[:2], [*LIGHTS[:2], 'additional-light'])
