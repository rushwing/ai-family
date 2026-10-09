"""TC-018-05: real Capability validation precedes real State convergence."""

from copy import deepcopy

import pytest
from action_support import changed, evidence, reject, request, required, result, running
from capability_support import catalogue, descriptor, obj
from state_support import observation

pytestmark = required


@pytest.mark.parametrize('position', [False, True])
def test_false_zero_observed_success(action_api, inventory, initial_cat, position):
    t = running(action_api, inventory, initial_cat, request(position))
    e = evidence(t, 'state')
    before = deepcopy(e)
    done = action_api.transition_task(t, result(t, 'succeeded', evidence=e, present=True),
                                      inventory=inventory, catalogue=initial_cat)
    assert done['state'] == 'succeeded'
    assert e == before and e['state']['desired_state'] is None
    assert done['result']['evidence']['state'] == e['state']


@pytest.mark.parametrize('path,value', [
    (['availability', 'status'], 'offline'), (['availability', 'status'], 'unknown'),
    (['availability', 'ordering'], {'epoch': 0, 'sequence': 2}),
    (['reported_state'], {}), (['reported_state', 'is_on', 'value'], True),
    (['reported_state', 'is_on', 'value'], 0),
    (['reported_state', 'is_on', 'ordering'], {'epoch': 1, 'sequence': 1}),
    (['reported_state', 'is_on', 'ordering'], {'epoch': 1, 'sequence': 0}),
    (['reported_state', 'is_on', 'ordering'], {'epoch': 0, 'sequence': 999}),
    (['reported_state', 'is_on', 'ordering'], {'epoch': 2, 'sequence': 2}),
    (['home_id'], 'other-home'), (['device_id'], 'device-bedroom-light-02'),
])
def test_state_negative(action_api, inventory, initial_cat, path, value):
    t = running(action_api, inventory, initial_cat)
    e = evidence(t, 'state')
    e['state'] = changed(e['state'], path, value)
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=e), inventory=inventory, catalogue=initial_cat))


@pytest.mark.parametrize('value', [0.0, 100.0, -1, 101, True, '0', None])
def test_canonical_position_observations(action_api, inventory, initial_cat, value):
    t = running(action_api, inventory, initial_cat, request(True))
    e = evidence(t, 'state')
    e['state']['reported_state']['position_percent']['value'] = value
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=e), inventory=inventory, catalogue=initial_cat))


@pytest.mark.parametrize('baseline', [None, {'epoch': 0, 'sequence': 0}])
def test_missing_cross_epoch_baseline(action_api, inventory, initial_cat, baseline):
    t = running(action_api, inventory, initial_cat,
                dispatch={'current_epoch': 1, 'baseline': baseline})
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=evidence(t, 'state')),
        inventory=inventory, catalogue=initial_cat))


def test_unknown_observation(action_api, inventory, initial_cat):
    t = running(action_api, inventory, initial_cat)
    e = evidence(t, 'state')
    e['state']['reported_state']['is_on'] = {
        'status': 'unknown', 'value': None, 'ordering': None, 'observed_at': None}
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=e), inventory=inventory, catalogue=initial_cat))


def test_untrusted_desired_cannot_select_targets(action_api, inventory, initial_cat):
    t = running(action_api, inventory, initial_cat)
    e = evidence(t, 'state')
    e['state']['reported_state']['is_on']['value'] = True
    e['state']['desired_state'] = {
        'revision': 99, 'values': {'is_on': True},
        'report_baseline': {'epoch': 1, 'sequence': 0}}
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=e), inventory=inventory, catalogue=initial_cat))


def test_multiple_and_constant_targets(action_api, inventory):
    d = descriptor()
    d['properties']['level'] = {
        'title': 'Level', 'description': 'Fictional integer level.', 'read_only': False,
        'value_schema': {'type': 'integer', 'minimum': 0, 'maximum': 100}}
    a = d['actions']['set_power']
    a['output_schema'] = {'type': 'null'}
    a['input_schema'] = obj({'power': {'type': 'boolean'}})
    a['completion_policy']['targets']['level'] = {'source': 'constant', 'value': 0}
    cat = catalogue(d)
    r = request()
    r.update(capability_id='demo.power', action_id='set_power', arguments={'power': False})
    t = running(action_api, inventory, cat, r)
    e = evidence(t, 'state')
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=e), inventory=inventory, catalogue=cat))
    e['state']['reported_state']['level'] = observation(0)
    done = action_api.transition_task(t, result(t, 'succeeded', evidence=e),
                                      inventory=inventory, catalogue=cat)
    assert done['state'] == 'succeeded'
    e['state']['reported_state']['level'] = observation(1)
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=e), inventory=inventory, catalogue=cat))
