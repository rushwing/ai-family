"""TC-018-01: strict external and contextual request boundaries."""

from copy import deepcopy

import pytest
from action_support import changed, make, reject, request, requester, required

pytestmark = required


@pytest.mark.parametrize('field', list(request()))
@pytest.mark.parametrize('mode', ['missing', 'null', 'wrong'])
def test_required_fields(action_api, inventory, initial_cat, field, mode):
    r = request()
    if mode == 'missing':
        del r[field]
    else:
        r[field] = None if mode == 'null' else []
    reject(action_api, lambda: make(action_api, inventory, initial_cat, r))


@pytest.mark.parametrize('field', ['idempotency_key', 'trace_id', 'task_id'])
@pytest.mark.parametrize('value', ['', ' abc', 'abc ', 'a b', '\n', 'x\x00', 'é', 'a/b', 'x'*129,
                                   True, 1])
def test_token_rejections(action_api, inventory, initial_cat, field, value):
    r = request()
    if field == 'task_id':
        reject(action_api, lambda: action_api.create_task(
            r, requester=requester(), task_id=value, inventory=inventory, catalogue=initial_cat))
    else:
        r[field] = value
        reject(action_api, lambda: make(action_api, inventory, initial_cat, r))


@pytest.mark.parametrize('value', ['x', 'X'*128, 'A._:-09'])
def test_token_boundaries(action_api, inventory, initial_cat, value):
    r = request()
    r.update(idempotency_key=value, trace_id=value)
    t = action_api.create_task(r, requester=requester(), task_id=value,
                               inventory=inventory, catalogue=initial_cat)
    assert t['task_id'] == t['trace_id'] == value
    assert t['request'] == r


@pytest.mark.parametrize('field,value', [
    ('schema_version', True), ('schema_version', 2), ('capability_version', True),
    ('capability_version', 0), ('capability_version', 2), ('capability_id', 'vendor/service'),
    ('device_id', 'missing-device'), ('home_id', 'other-home'), ('action_id', 'reset'),
    ('capability_id', 'home.temperature_sensor'), ('arguments', {}),
    ('arguments', {'is_on': 0}), ('arguments', {'is_on': False, 'secret': 1}),
])
def test_contextual_rejection(action_api, inventory, initial_cat, field, value):
    reject(action_api, lambda: make(action_api, inventory, initial_cat,
                                    changed(request(), [field], value)))


@pytest.mark.parametrize('value', [0, 100])
def test_position_valid(action_api, inventory, initial_cat, value):
    r = request(True)
    r['arguments']['position_percent'] = value
    assert make(action_api, inventory, initial_cat, r)['request'] == r


@pytest.mark.parametrize('value', [-1, 101, 0.0, 100.0, True, '0', None])
def test_position_invalid(action_api, inventory, initial_cat, value):
    r = request(True)
    r['arguments']['position_percent'] = value
    reject(action_api, lambda: make(action_api, inventory, initial_cat, r))


@pytest.mark.parametrize('key', ['requester', 'role', 'trusted', 'scope', 'authorization',
                                  'confirmation', 'completion_policy', 'private-credential'])
def test_spoofed_wire_fields(action_api, inventory, initial_cat, key):
    r = {**request(), key: 'SECRET-VALUE'}
    reject(action_api, lambda: make(action_api, inventory, initial_cat, r),
           private=('SECRET-VALUE', 'private-credential'))


@pytest.mark.parametrize('field', list(requester()))
@pytest.mark.parametrize('value', [None, '', [], True])
def test_bad_requester(action_api, inventory, initial_cat, field, value):
    who = changed(requester(), [field], value)
    reject(action_api, lambda: make(action_api, inventory, initial_cat, who=who))


@pytest.mark.parametrize('who', [None, {}, {**requester(), 'home_id': 'another-home'},
                                  {**requester(), 'role': 'guest'},
                                  {**requester(), 'trusted': True}])
def test_missing_or_mismatched_context(action_api, inventory, initial_cat, who):
    reject(action_api, lambda: action_api.validate_request(
        request(), requester=who, inventory=inventory, catalogue=initial_cat))


@pytest.mark.parametrize('role', ['admin', 'adult', 'kid'])
def test_all_roles_are_shape_not_authorization(action_api, inventory, initial_cat, role):
    who = {**requester(), 'role': role}
    t = make(action_api, inventory, initial_cat, who=who)
    assert t['requester'] == who
    assert t['state'] == 'accepted' and t['result'] is None


def test_upstream_failures_and_input_isolation(action_api, inventory, initial_cat):
    r = request()
    original = deepcopy(r)
    for inv, cat in [({'PRIVATE-FIELD': 'SECRET-VALUE'}, initial_cat), (inventory, {})]:
        reject(action_api, lambda: make(action_api, inv, cat, r),
               private=('PRIVATE-FIELD', 'SECRET-VALUE'))
    assert r == original
