"""TC-013-06: malformed selection is distinct from empty results; pure calls."""

import builtins
import io
import os
from copy import deepcopy

import pytest
from inventory_support import assert_error, assert_targets, resolve, runtime_required

pytestmark = runtime_required


@pytest.mark.parametrize('selector,path', [
    ({}, ('selector',)),
    ({'area_ids': ['area-bedroom-01'], 'area_group_ids': ['resting']}, ('selector',)),
    *[({key: value}, ('selector', key))
      for key in ('area_ids', 'area_group_ids')
      for value in ([], None, 'resting', 1, True, {})],
    ({'area_ids': ['area-bedroom-01', 'area-bedroom-01']}, ('selector', 'area_ids', 1)),
    ({'area_group_ids': ['resting', 'resting']}, ('selector', 'area_group_ids', 1)),
    ({'area_ids': ['missing']}, ('selector', 'area_ids', 0)),
    ({'area_ids': ['resting']}, ('selector', 'area_ids', 0)),
    ({'area_group_ids': ['missing']}, ('selector', 'area_group_ids', 0)),
    ({'area_group_ids': ['area-bedroom-01']}, ('selector', 'area_group_ids', 0)),
    *[({key: [value]}, ('selector', key, 0))
      for key in ('area_ids', 'area_group_ids') for value in (None, True, 1, [], {})],
    ({'area_group_ids': ['resting'], 'label_ids': ['missing']}, ('selector', 'label_ids', 0)),
    ({'area_group_ids': ['resting'], 'label_ids': ['primary', 'primary']},
     ('selector', 'label_ids', 1)),
    ({'area_group_ids': ['resting'], 'label_ids': ['floor-0']}, ('selector', 'label_ids', 0)),
    *[({'area_group_ids': ['resting'], 'label_ids': value}, ('selector', 'label_ids'))
      for value in (None, 'primary', 1, True, {})],
    *[({'area_group_ids': ['resting'], 'label_ids': [value]}, ('selector', 'label_ids', 0))
      for value in (None, True, 1, [], {})],
])
def test_invalid_selector_paths_and_no_mutation(api, inventory, selector, path):
    data = api.validate_inventory(inventory)
    before = deepcopy(data), deepcopy(selector)
    assert_error(api, lambda: resolve(api, data, selector), path)
    assert (data, selector) == before


@pytest.mark.parametrize('selector', [None, [], 'resting', 1, True])
def test_selector_must_be_object(api, inventory, selector):
    assert_error(api, lambda: resolve(api, api.validate_inventory(inventory), selector),
                 ('selector',))


@pytest.mark.parametrize('home_id', ['different-home', 'home-missing', None, 1, True])
def test_wrong_home_fails_without_targets(api, inventory, home_id):
    data = api.validate_inventory(inventory)
    assert_error(api, lambda: resolve(api, data, {'area_group_ids': ['resting']}, home_id),
                 ('home_id',))


@pytest.mark.parametrize('selector,areas,devices', [
    ({'area_group_ids': ['resting'], 'label_ids': ['children']},
     ['area-bedroom-02'], ['device-bedroom-light-02']),
    ({'area_group_ids': ['studio']}, [], []),
    ({'area_ids': ['area-living-room']}, ['area-living-room'], []),
    ({'area_ids': ['unknown']}, None, None),
])
def test_resolver_cannot_write_or_mutate(api, inventory, monkeypatch, selector, areas, devices):
    data = api.validate_inventory(inventory)
    before = deepcopy(data), deepcopy(selector)
    attempts = []
    real_open, real_io_open, real_os_open = builtins.open, io.open, os.open

    def guarded_open(original):
        def call(file, mode='r', *args, **kwargs):
            if any(c in mode for c in 'wax+'):
                attempts.append('file write')
                raise AssertionError('Resolver attempted a file write')
            return original(file, mode, *args, **kwargs)
        return call

    def guarded_os_open(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            attempts.append('file write')
            raise AssertionError('Resolver attempted a file write')
        return real_os_open(file, flags, *args, **kwargs)

    def deny(*args, **kwargs):
        attempts.append('filesystem mutation')
        raise AssertionError('Resolver attempted filesystem mutation')

    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'open', guarded_open(real_open))
        patch.setattr(io, 'open', guarded_open(real_io_open))
        patch.setattr(os, 'open', guarded_os_open)
        for name in ('remove', 'unlink', 'rename', 'replace', 'mkdir', 'rmdir', 'system'):
            patch.setattr(os, name, deny, raising=False)
        if areas is None:
            assert_error(api, lambda: resolve(api, data, selector), ('selector', 'area_ids', 0))
        else:
            assert_targets(resolve(api, data, selector), areas, devices)
    assert not attempts
    assert (data, selector) == before
