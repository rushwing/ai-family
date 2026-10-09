"""TC-018-03: complete transition matrix and contextual result consistency."""

from copy import deepcopy

import pytest
from action_support import (
    STATES,
    changed,
    custom,
    evidence,
    make,
    reject,
    required,
    result,
    running,
)

pytestmark = required
EDGES = {
    'accepted': {'running', 'failed', 'timed_out', 'cancelled'},
    'running': {'acknowledged', 'succeeded', 'failed', 'timed_out', 'cancelled'},
}


def seed(api, inventory, initial_cat, state):
    cat = initial_cat
    r = None
    if state == 'acknowledged':
        cat, r = custom('ack_only')
    if state == 'accepted':
        return cat, make(api, inventory, cat, r)
    t = running(api, inventory, cat, r)
    if state != 'running':
        e = evidence(t, 'ack' if state == 'acknowledged' else 'state')
        out = result(t, state, evidence=e if state in ('acknowledged', 'succeeded') else None)
        t = api.transition_task(t, out, inventory=inventory, catalogue=cat)
    return cat, t


@pytest.mark.parametrize('before', STATES)
@pytest.mark.parametrize('after', STATES)
def test_every_transition(action_api, inventory, initial_cat, before, after):
    # The running -> acknowledged edge uses its actual policy, not a mock helper.
    if before == 'running' and after == 'acknowledged':
        cat, r = custom('ack_only')
        t = running(action_api, inventory, cat, r)
    else:
        cat, t = seed(action_api, inventory, initial_cat, before)
    if before == after:
        out = t['result'] if t['result'] is not None else result(t, 'accepted')
    else:
        out = result(t, after, evidence=(evidence(t, 'ack' if after == 'acknowledged' else 'state')
                                        if after in ('acknowledged', 'succeeded') else None))
    original = deepcopy(t)
    kwargs = {'inventory': inventory, 'catalogue': cat}
    if before == 'accepted' and after == 'running':
        kwargs['dispatch_context'] = {'current_epoch': 1, 'baseline': {'epoch': 1, 'sequence': 1}}
    def call():
        return action_api.transition_task(t, out, **kwargs)

    if before == after or after in EDGES.get(before, set()):
        updated = call()
        assert updated['state'] == after
        assert action_api.validate_task(updated, inventory=inventory, catalogue=cat) == updated
    else:
        reject(action_api, call)
    assert t == original


@pytest.mark.parametrize('path,value', [
    (['state'], 'completed'), (['task_id'], 'other-task'), (['trace_id'], 'other-trace'),
    (['device_id'], 'device-bedroom-light-02'), (['home_id'], 'another-home'),
    (['capability_id'], 'home.positionable'), (['capability_version'], 2),
    (['action_id'], 'other'), (['schema_version'], True),
    (['error'], {'code': 'failure'}), (['physical_outcome'], 'confirmed'),
    (['output'], {'present': False, 'value': True}),
    (['output'], {'present': True, 'value': {'accepted': True}}),
    (['output'], {'present': 1, 'value': None}),
    (['output'], {'present': False}), (['error'], {'code': 'x', 'message': 'private'}),
])
def test_invalid_result(action_api, inventory, initial_cat, path, value):
    t = running(action_api, inventory, initial_cat)
    out = changed(result(t), path, value)
    reject(action_api, lambda: action_api.validate_result(
        out, task=t, inventory=inventory, catalogue=initial_cat))


@pytest.mark.parametrize('state', ['failed', 'timed_out', 'cancelled'])
def test_terminal_variants(action_api, inventory, initial_cat, state):
    t = make(action_api, inventory, initial_cat)
    out = result(t, state)
    finished = action_api.transition_task(t, out, inventory=inventory, catalogue=initial_cat)
    assert finished['result']['physical_outcome'] == 'unverified'
    for field, value in [('evidence', evidence(t)), ('physical_outcome', 'confirmed')]:
        reject(action_api, lambda: action_api.transition_task(
            t, {**out, field: value}, inventory=inventory, catalogue=initial_cat))
    if state != 'cancelled':
        for code in [None, '', 'bad code', 'x'*129]:
            reject(action_api, lambda: action_api.transition_task(
                t, {**out, 'error': {'code': code}}, inventory=inventory, catalogue=initial_cat))


@pytest.mark.parametrize('path,value', [
    (['completion_policy'], {'kind': 'ack_only'}), (['trace_id'], 'other'),
    (['state'], 'completed'), (['schema_version'], 2),
    (['dispatch_context', 'current_epoch'], True),
    (['dispatch_context', 'baseline'], {'epoch': -1, 'sequence': 1}),
    (['result'], None),
])
def test_invalid_task(action_api, inventory, initial_cat, path, value):
    cat, t = seed(action_api, inventory, initial_cat, 'succeeded')
    reject(action_api, lambda: action_api.validate_task(
        changed(t, path, value), inventory=inventory, catalogue=cat))


def test_frozen_dispatch_and_conflicting_replay(action_api, inventory, initial_cat):
    t = running(action_api, inventory, initial_cat)
    reject(action_api, lambda: action_api.transition_task(
        t, result(t), inventory=inventory, catalogue=initial_cat,
        dispatch_context={'current_epoch': 2, 'baseline': None}))
    out = result(t, present=True)
    reject(action_api, lambda: action_api.transition_task(
        t, out, inventory=inventory, catalogue=initial_cat))
    assert action_api.validate_result(out, task=t, inventory=inventory,
                                      catalogue=initial_cat)['output']['value'] is None


def test_running_requires_context(action_api, inventory, initial_cat):
    t = make(action_api, inventory, initial_cat)
    reject(action_api, lambda: action_api.transition_task(
        t, result(t), inventory=inventory, catalogue=initial_cat))


@pytest.mark.parametrize('factory', ['Task', 'ActionResult'])
@pytest.mark.parametrize('mode', ['missing', 'unknown'])
def test_every_envelope_field(action_api, inventory, initial_cat, factory, mode):
    t = running(action_api, inventory, initial_cat)
    value = t if factory == 'Task' else result(t)
    if mode == 'missing':
        for field in value:
            broken = {k: v for k, v in value.items() if k != field}
            reject(action_api, lambda: getattr(action_api, factory).from_dict(broken))
    else:
        reject(action_api, lambda: getattr(action_api, factory).from_dict(
            {**value, 'PRIVATE-KEY': 'PRIVATE-VALUE'}), private=('PRIVATE-KEY', 'PRIVATE-VALUE'))


@pytest.mark.parametrize('field', ['task_id', 'trace_id'])
@pytest.mark.parametrize('value', ['', 'x'*129, ' x', 'x ', 'x\x00', 'é', 1, None])
def test_result_and_evidence_tokens(action_api, inventory, initial_cat, field, value):
    t = running(action_api, inventory, initial_cat)
    out = result(t, 'succeeded', evidence=evidence(t, 'state'))
    for container in [out, out['evidence']]:
        original = container[field]
        container[field] = value
        reject(action_api, lambda: action_api.ActionResult.from_dict(out))
        container[field] = original


def test_persisted_success_revalidated(action_api, inventory, initial_cat):
    cat, t = seed(action_api, inventory, initial_cat, 'succeeded')
    t['result']['evidence'] = evidence(t)  # structurally valid ACK, false success label
    reject(action_api, lambda: action_api.validate_task(t, inventory=inventory, catalogue=cat))
    cat, t = seed(action_api, inventory, initial_cat, 'succeeded')
    t['result']['evidence']['state']['reported_state']['is_on']['value'] = True
    # Shape-only factory may load the record, but contextual completion cannot confirm it.
    assert action_api.Task.from_dict(t).state == 'succeeded'
    reject(action_api, lambda: action_api.validate_task(t, inventory=inventory, catalogue=cat))
