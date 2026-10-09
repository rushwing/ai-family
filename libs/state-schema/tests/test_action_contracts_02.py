"""TC-018-02: scoped replay classification preserves exact primitive types."""

import pytest
from action_support import changed, custom, make, reject, request, requester, required

pytestmark = required


@pytest.mark.parametrize('field,value,expected', [
    ('trace_id', 'new-trace', 'replay'), ('idempotency_key', 'new-key', 'distinct'),
    ('idempotency_key', 'KEY-1', 'distinct'),
    ('device_id', 'device-bedroom-light-02', 'conflict'),
    ('arguments', {'is_on': True}, 'conflict'),
    ('capability_id', 'home.positionable', 'invalid'),
])
def test_comparison(action_api, inventory, initial_cat, field, value, expected):
    t = make(action_api, inventory, initial_cat)
    r = changed(request(), [field], value)
    def call():
        return action_api.compare_idempotency(
            t, r, requester=requester(), inventory=inventory, catalogue=initial_cat)

    if expected == 'invalid':
        reject(action_api, call)
    else:
        assert call() == expected
    assert t['task_id'] == 'task-1' and t['trace_id'] == 'trace-1'


@pytest.mark.parametrize('field', ['subject_id', 'family_member_id'])
def test_requester_scope(action_api, inventory, initial_cat, field):
    t = make(action_api, inventory, initial_cat)
    assert action_api.compare_idempotency(t, request(), requester={**requester(), field: 'other'},
                                          inventory=inventory, catalogue=initial_cat) == 'distinct'


def test_numeric_type_conflict(action_api, inventory):
    cat, r = custom('ack_only', number=True)
    t = make(action_api, inventory, cat, r)
    assert action_api.compare_idempotency(t, r, requester=requester(), inventory=inventory,
                                          catalogue=cat) == 'replay'
    r['arguments']['power'] = 230.0
    assert action_api.compare_idempotency(t, r, requester=requester(), inventory=inventory,
                                          catalogue=cat) == 'conflict'


def test_nested_key_order_and_types(action_api, inventory):
    cat, r = custom('ack_only')
    cat['capabilities'][0]['actions']['set_power']['input_schema'] = {
        'type': 'object', 'properties': {'data': {
            'type': 'array', 'items': {'type': 'object', 'properties': {
                'a': {'type': 'number'}, 'b': {'type': 'boolean'}},
                'required': ['a', 'b'], 'additionalProperties': False}}},
        'required': ['data'], 'additionalProperties': False}
    r['arguments'] = {'data': [{'a': 1, 'b': False}]}
    t = make(action_api, inventory, cat, r)
    r['arguments'] = {'data': [{'b': False, 'a': 1}]}
    assert action_api.compare_idempotency(t, r, requester=requester(), inventory=inventory,
                                          catalogue=cat) == 'replay'
    r['arguments']['data'][0]['a'] = 1.0
    assert action_api.compare_idempotency(t, r, requester=requester(), inventory=inventory,
                                          catalogue=cat) == 'conflict'


def test_changed_revision_and_action(action_api, inventory):
    cat, r = custom('ack_only')
    from copy import deepcopy
    second = deepcopy(cat['capabilities'][0])
    second['capability_version'] = 2
    cat['capabilities'].append(second)
    second['actions']['other'] = deepcopy(second['actions']['set_power'])
    t = make(action_api, inventory, cat, r)
    r['capability_version'] = 2
    for action in ['set_power', 'other']:
        r['action_id'] = action
        assert action_api.compare_idempotency(t, r, requester=requester(), inventory=inventory,
                                              catalogue=cat) == 'conflict'


def test_invalid_existing_task_is_not_replayed(action_api, inventory, initial_cat):
    t = make(action_api, inventory, initial_cat)
    t['trace_id'] = 'different'
    reject(action_api, lambda: action_api.compare_idempotency(
        t, request(), requester=requester(), inventory=inventory, catalogue=initial_cat))
