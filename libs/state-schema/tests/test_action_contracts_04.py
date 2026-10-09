"""TC-018-04: ACK has no physical-success authority; events need correlation/order."""

import pytest
from action_support import changed, custom, evidence, make, reject, required, result, running

pytestmark = required


@pytest.mark.parametrize('kind', ['ack_only', 'event_confirmed', 'state_converged'])
def test_ack_never_succeeds(action_api, inventory, initial_cat, kind):
    if kind == 'state_converged':
        cat, r = initial_cat, None
    else:
        cat, r = custom(kind)
    t = running(action_api, inventory, cat, r)
    for e in [None, evidence(t)]:
        reject(action_api, lambda: action_api.transition_task(
            t, result(t, 'succeeded', evidence=e, present=True),
            inventory=inventory, catalogue=cat))
    out = result(t, 'acknowledged', evidence=evidence(t), present=True)
    if kind == 'ack_only':
        done = action_api.transition_task(t, out, inventory=inventory, catalogue=cat)
        assert done['state'] == 'acknowledged'
        assert done['result']['physical_outcome'] == 'unverified'
    else:
        reject(action_api, lambda: action_api.transition_task(
            t, out, inventory=inventory, catalogue=cat))


@pytest.mark.parametrize('terminal', ['acknowledged', 'succeeded'])
def test_immediate_evidence_requires_running(action_api, inventory, terminal):
    cat, r = custom('ack_only' if terminal == 'acknowledged' else 'event_confirmed')
    t = make(action_api, inventory, cat, r)
    kind = 'ack' if terminal == 'acknowledged' else 'event'
    out = result(t, terminal, evidence=evidence(t, kind))
    reject(action_api, lambda: action_api.transition_task(
        t, out, inventory=inventory, catalogue=cat))


def test_event_confirmed(action_api, inventory):
    cat, r = custom()
    t = running(action_api, inventory, cat, r)
    out = result(t, 'succeeded', evidence=evidence(t, 'event'), present=True)
    done = action_api.transition_task(t, out, inventory=inventory, catalogue=cat)
    assert done['state'] == 'succeeded' and done['result']['physical_outcome'] == 'confirmed'


@pytest.mark.parametrize('path,value', [
    (['task_id'], 'wrong'), (['trace_id'], 'wrong'), (['home_id'], 'wrong'),
    (['device_id'], 'wrong'), (['capability_id'], 'demo.other'),
    (['capability_version'], 2), (['action_id'], 'wrong'),
    (['event'], 'missing'), (['payload'], {'power': 0}), (['payload'], {}),
    (['ordering'], {'epoch': 0, 'sequence': 999}),
    (['ordering'], {'epoch': 2, 'sequence': 2}),
    (['ordering'], {'epoch': 1, 'sequence': 1}),
    (['ordering'], {'epoch': 1, 'sequence': 0}),
    (['ordering'], None), (['kind'], 'provider_success'),
])
def test_event_negative(action_api, inventory, path, value):
    cat, r = custom()
    t = running(action_api, inventory, cat, r)
    e = changed(evidence(t, 'event'), path, value)
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=e), inventory=inventory, catalogue=cat))


@pytest.mark.parametrize('baseline', [None, {'epoch': 0, 'sequence': 1},
                                      {'epoch': 2, 'sequence': 1}])
def test_ineligible_event_baseline(action_api, inventory, baseline):
    cat, r = custom()
    t = running(action_api, inventory, cat, r,
                dispatch={'current_epoch': 1, 'baseline': baseline})
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'succeeded', evidence=evidence(t, 'event')),
        inventory=inventory, catalogue=cat))


def test_running_can_record_ack_without_success(action_api, inventory):
    cat, r = custom()
    t = make(action_api, inventory, cat, r)
    started = action_api.transition_task(t, result(t, evidence=evidence(t), present=True),
                                         inventory=inventory, catalogue=cat,
                                         dispatch_context={'current_epoch': 1, 'baseline': None})
    assert started['state'] == 'running'
    assert started['result']['physical_outcome'] == 'unverified'


@pytest.mark.parametrize('field', ['task_id', 'trace_id', 'home_id', 'device_id',
                                   'capability_id', 'capability_version', 'action_id'])
def test_ack_correlation(action_api, inventory, field):
    cat, r = custom('ack_only')
    t = running(action_api, inventory, cat, r)
    e = evidence(t)
    e[field] = 2 if field == 'capability_version' else (
        'demo.other' if field == 'capability_id' else 'other')
    reject(action_api, lambda: action_api.transition_task(
        t, result(t, 'acknowledged', evidence=e), inventory=inventory, catalogue=cat))


@pytest.mark.parametrize('kind', ['ack', 'event', 'state'])
def test_evidence_fields(action_api, inventory, initial_cat, kind):
    cat, r = custom() if kind == 'event' else (initial_cat, None)
    t = running(action_api, inventory, cat, r)
    e = evidence(t, kind)
    state = 'running' if kind == 'ack' else 'succeeded'
    for field in e:
        broken = {k: v for k, v in e.items() if k != field}
        reject(action_api, lambda: action_api.ActionResult.from_dict(
            result(t, state, evidence=broken)))
    reject(action_api, lambda: action_api.ActionResult.from_dict(
        result(t, state, evidence={**e, 'PRIVATE-KEY': 'PRIVATE-VALUE'})),
        private=('PRIVATE-KEY', 'PRIVATE-VALUE'))
