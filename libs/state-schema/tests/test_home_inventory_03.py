"""TC-013-03: single-fault validation matrices with deterministic paths."""

from copy import deepcopy
from itertools import combinations

import pytest
from inventory_support import KINDS, assert_error, at, changed, object_path, runtime_required

pytestmark = runtime_required
REQUIRED = [
    ('schema_version',), ('home',), ('floors',), ('areas',), ('devices',),
    ('labels',), ('area_groups',),
    *[(*object_path(kind), field) for kind, fields in {
        'home': ['id', 'name', 'residence_type'],
        'floors': ['id', 'home_id', 'name', 'level'],
        'areas': ['id', 'home_id', 'area_type', 'name', 'floor_id'],
        'devices': ['id', 'home_id', 'name', 'area_id'],
        'labels': ['id', 'name'],
        'area_groups': ['id', 'name', 'area_types'],
    }.items() for field in fields],
]
STRING_PATHS = [p for p in REQUIRED if p[-1] in {'id', 'home_id', 'name',
                                               'residence_type', 'area_type'}]
LIST_PATHS = [(kind,) for kind in KINDS if kind != 'home'] + [
    ('floors', 0, 'aliases'), ('areas', 0, 'aliases'), ('areas', 0, 'labels'),
    ('devices', 0, 'labels'), ('area_groups', 0, 'area_types'),
]


@pytest.mark.parametrize('path', REQUIRED)
def test_missing_required_fields(api, inventory, path):
    data = deepcopy(inventory)
    del at(data, path[:-1])[path[-1]]
    assert_error(api, lambda: api.validate_inventory(data), path)
    assert api.validate_inventory(inventory) == inventory


@pytest.mark.parametrize('path', STRING_PATHS)
@pytest.mark.parametrize('value', [None, 1, True, [], {}])
def test_wrong_string_types(api, inventory, path, value):
    data = changed(inventory, path, value)
    assert_error(api, lambda: api.validate_inventory(data), path)


@pytest.mark.parametrize('path', LIST_PATHS)
@pytest.mark.parametrize('value', [None, 'not-a-list', 1, True, {}])
def test_wrong_list_types(api, inventory, path, value):
    data = changed(inventory, path, value)
    assert_error(api, lambda: api.validate_inventory(data), path)


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('value', [None, 'not-an-object', 1, True, []])
def test_wrong_object_types(api, inventory, kind, value):
    path = object_path(kind)
    assert_error(api, lambda: api.validate_inventory(changed(inventory, path, value)), path)


@pytest.mark.parametrize('path', [('schema_version',), ('floors', 0, 'level')])
@pytest.mark.parametrize('value', [None, True, False, '1', 1.5, [], {}])
def test_strict_integer_types(api, inventory, path, value):
    assert_error(api, lambda: api.validate_inventory(changed(inventory, path, value)), path)


@pytest.mark.parametrize('version', [0, 2, -1])
def test_unsupported_version(api, inventory, version):
    data = changed(inventory, ('schema_version',), version)
    assert_error(api, lambda: api.validate_inventory(data), ('schema_version',))


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('value', ['', 'A', '1abc', 'a b', 'a.b', 'a' * 65])
def test_invalid_id_spellings(api, inventory, kind, value):
    path = (*object_path(kind), 'id')
    assert_error(api, lambda: api.validate_inventory(changed(inventory, path, value)), path)


@pytest.mark.parametrize('value', ['a', 'a' * 64, 'label-example-02', 'label_example_02'])
def test_valid_id_boundaries(api, inventory, value):
    # An unreferenced label permits a single-field identity mutation.
    data = changed(inventory, ('labels', 1, 'id'), value)
    assert api.validate_inventory(data) == data


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('value', ['', ' ', '\t', ' untrimmed', 'untrimmed '])
def test_invalid_names(api, inventory, kind, value):
    path = (*object_path(kind), 'name')
    assert_error(api, lambda: api.validate_inventory(changed(inventory, path, value)), path)


@pytest.mark.parametrize('kind', [k for k in KINDS if k != 'home'])
def test_duplicate_ids_within_kind(api, inventory, kind):
    data = deepcopy(inventory)
    data[kind].append(deepcopy(data[kind][0]))
    assert_error(api, lambda: api.validate_inventory(data), (kind, len(data[kind]) - 1, 'id'))


@pytest.mark.parametrize('earlier,later', list(combinations(KINDS, 2)))
def test_global_id_collisions(api, inventory, earlier, later):
    path = (*object_path(later), 'id')
    value = at(inventory, (*object_path(earlier), 'id'))
    data = changed(inventory, path, value)
    old_id = at(inventory, path)
    # Keep references valid so this is a collision, not a dangling-reference test.
    if later == 'floors':
        for area in data['areas']:
            if area['floor_id'] == old_id:
                area['floor_id'] = value
    elif later == 'areas':
        for device in data['devices']:
            if device['area_id'] == old_id:
                device['area_id'] = value
    elif later == 'labels':
        for record in [*data['areas'], *data['devices']]:
            record['labels'] = [value if label == old_id else label for label in record['labels']]
    assert_error(api, lambda: api.validate_inventory(data), path)


@pytest.mark.parametrize('path,value,error_path', [
    (('home', 'residence_type'), 'castle', ('home', 'residence_type')),
    (('areas', 0, 'area_type'), 'bedrom', ('areas', 0, 'area_type')),
    (('floors', 0, 'aliases'), [''], ('floors', 0, 'aliases', 0)),
    (('areas', 0, 'aliases'), ['a', 'a'], ('areas', 0, 'aliases', 1)),
    (('floors', 0, 'aliases'), ['a', 'a'], ('floors', 0, 'aliases', 1)),
    (('areas', 0, 'aliases'), [True], ('areas', 0, 'aliases', 0)),
    (('devices', 0, 'labels'), ['primary', 'primary'], ('devices', 0, 'labels', 1)),
    (('areas', 0, 'labels'), ['primary', 'primary'], ('areas', 0, 'labels', 1)),
    (('areas', 0, 'labels'), ['childen'], ('areas', 0, 'labels', 0)),
    (('devices', 0, 'labels'), ['missing'], ('devices', 0, 'labels', 0)),
    (('areas', 0, 'labels'), [1], ('areas', 0, 'labels', 0)),
    (('devices', 0, 'labels'), [True], ('devices', 0, 'labels', 0)),
    (('area_groups', 0, 'area_types'), [], ('area_groups', 0, 'area_types')),
    (('area_groups', 0, 'area_types'), ['bedroom', 'bedroom'],
     ('area_groups', 0, 'area_types', 1)),
    (('area_groups', 0, 'area_types'), ['bedrom'], ('area_groups', 0, 'area_types', 0)),
    (('area_groups', 0, 'area_types'), [True], ('area_groups', 0, 'area_types', 0)),
])
def test_vocabulary_and_list_members(api, inventory, path, value, error_path):
    assert_error(api, lambda: api.validate_inventory(changed(inventory, path, value)), error_path)


@pytest.mark.parametrize('kind', ['floors', 'areas', 'devices'])
@pytest.mark.parametrize('home_id', ['home-missing', 'different-home'])
def test_cross_home_references(api, inventory, kind, home_id):
    path = (kind, 0, 'home_id')
    assert_error(api, lambda: api.validate_inventory(changed(inventory, path, home_id)), path)


@pytest.mark.parametrize('path,value', [
    (('areas', 0, 'floor_id'), 'missing-floor'),
    (('areas', 0, 'floor_id'), 'device-bedroom-light-01'),
    (('devices', 0, 'area_id'), 'missing-area'),
    (('devices', 0, 'area_id'), 'floor-0'),
    (('areas', 0, 'floor_id'), True),
    (('devices', 0, 'area_id'), []),
    (('areas', 0, 'labels'), ['floor-0']),
])
def test_dangling_wrong_kind_and_malformed_references(api, inventory, path, value):
    expected = (*path, 0) if path[-1] == 'labels' else path
    assert_error(api, lambda: api.validate_inventory(changed(inventory, path, value)), expected)
