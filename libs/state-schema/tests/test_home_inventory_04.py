"""TC-013-04: real public fixture and ignored private-edit workflow."""

import json
from copy import deepcopy

from inventory_support import EXAMPLE, LIGHTS, PRESETS, ROOMS, ROOT, runtime_required

pytestmark = runtime_required


def test_public_apartment_fixture(api):
    original = EXAMPLE.read_bytes()
    data = api.load_inventory(EXAMPLE)
    assert data == json.loads(original.decode('utf-8'))
    bedrooms = [a for a in data['areas'] if a['area_type'] == 'bedroom']
    assert {a['id']: a['name'] for a in bedrooms} == dict(zip(
        ROOMS, ['Master Bedroom', "Daughter's Room", 'Elderly Bedroom'], strict=True))
    assert {d['id']: d['area_id'] for d in data['devices']} == dict(zip(LIGHTS, ROOMS, strict=True))
    assert {g['id']: g['area_types'] for g in data['area_groups']} == PRESETS
    assert 'children' in {label['id'] for label in data['labels']}
    assert bedrooms[1]['labels'] == ['children']
    assert 'childen' not in json.dumps(data)
    assert all(set(d) == {'id', 'home_id', 'name', 'area_id', 'labels'} for d in data['devices'])
    assert EXAMPLE.read_bytes() == original


def edited_copy(inventory):
    data = deepcopy(inventory)
    data['areas'][1]['name'] = 'Renamed fictional room'
    data['floors'].append({'id': 'floor-upper', 'home_id': 'home-example', 'name': 'Upper',
                           'level': 1, 'aliases': []})
    data['areas'][1]['floor_id'] = 'floor-upper'
    data['devices'][1]['name'] = 'Renamed fictional light'
    return data


def test_private_copy_loads_without_changing_public_fixture(api, inventory, tmp_path, launch):
    original = EXAMPLE.read_bytes()
    status_before = launch(['git', 'status', '--porcelain'], cwd=ROOT)
    assert status_before.returncode == 0
    private = tmp_path / 'example.home-inventory.local.json'
    data = edited_copy(inventory)
    private.write_text(json.dumps(data), encoding='utf-8')
    private_bytes = private.read_bytes()
    assert api.load_inventory(private) == data
    assert [a['id'] for a in data['areas']] == [a['id'] for a in inventory['areas']]
    assert [d['id'] for d in data['devices']] == [d['id'] for d in inventory['devices']]
    assert data['devices'][1]['area_id'] == data['areas'][1]['id']
    assert private.read_bytes() == private_bytes
    assert EXAMPLE.read_bytes() == original
    status_after = launch(['git', 'status', '--porcelain'], cwd=ROOT)
    assert status_after.returncode == 0
    assert status_after.stdout == status_before.stdout


def test_private_inventory_name_is_git_ignored(launch):
    # --no-index checks the real rule without creating a private file in the worktree.
    result = launch(['git', 'check-ignore', '--no-index',
                     'docs/product/home-intelligence/examples/test.home-inventory.local.json'],
                    cwd=ROOT)
    assert result.returncode == 0
    assert result.stdout.strip().endswith('test.home-inventory.local.json')
