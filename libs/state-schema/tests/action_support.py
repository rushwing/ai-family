"""Independently specified fictional envelopes for REQ-018 public API checks."""

from copy import deepcopy
from importlib.util import find_spec

import pytest
from capability_support import catalogue, descriptor, obj
from state_support import availability, observation, order

required = pytest.mark.skipif(
    find_spec('state_schema.action_contracts') is None,
    reason='REQ-018 Action runtime absent; acceptance pending',
)
STATES = ('accepted', 'running', 'acknowledged', 'succeeded', 'failed', 'timed_out', 'cancelled')
IDENTITY = ('home_id', 'device_id', 'capability_id', 'capability_version', 'action_id')


def request(position=False):
    return {
        'schema_version': 1, 'home_id': 'home-example',
        'device_id': 'device-bedroom-light-01',
        'capability_id': 'home.positionable' if position else 'home.switchable',
        'capability_version': 1, 'action_id': 'set_position' if position else 'set_on',
        'arguments': {'position_percent': 0} if position else {'is_on': False},
        'idempotency_key': 'key-1', 'trace_id': 'trace-1',
    }


def requester():
    return {'subject_id': 'subject-example', 'family_member_id': 'member-example',
            'home_id': 'home-example', 'role': 'adult'}


def custom(kind='event_confirmed', number=False):
    d = descriptor()
    a = d['actions']['set_power']
    a['output_schema'] = {'type': 'null'}
    a['completion_policy'] = ({'kind': kind, 'event': 'changed'}
                              if kind == 'event_confirmed' else {'kind': kind})
    if number:
        a['input_schema'] = obj({'power': {'type': 'number'}})
    r = request()
    r.update(capability_id='demo.power', action_id='set_power',
             arguments={'power': 230} if number else {'power': False})
    return catalogue(d), r


def make(api, inventory, cat, r=None, who=None):
    return api.create_task(request() if r is None else r,
                           requester=requester() if who is None else who,
                           task_id='task-1', inventory=inventory, catalogue=cat)


def result(task, state='running', *, evidence=None, output=None, present=False):
    r = task['request']
    return {
        'schema_version': 1, 'task_id': task['task_id'], 'trace_id': task['trace_id'],
        **{k: r[k] for k in IDENTITY}, 'state': state,
        'output': {'present': present, 'value': output},
        'error': {'code': 'provider_failed'} if state in ('failed', 'timed_out') else None,
        'evidence': evidence,
        'physical_outcome': 'confirmed' if state == 'succeeded' else 'unverified',
    }


def evidence(task, kind='ack'):
    r = task['request']
    e = {'kind': kind, 'task_id': task['task_id'], 'trace_id': task['trace_id'],
         **{k: r[k] for k in IDENTITY}}
    if kind == 'event':
        e.update(event='changed', payload={'power': False}, ordering=order())
    elif kind == 'state':
        member, value = next(iter(r['arguments'].items()))
        e['state'] = {
            'home_id': r['home_id'], 'device_id': r['device_id'], 'desired_state': None,
            'reported_state': {member: observation(value)}, 'availability': availability(),
        }
    return e


def running(api, inventory, cat, r=None, dispatch=None):
    t = make(api, inventory, cat, r)
    return api.transition_task(t, result(t), inventory=inventory, catalogue=cat,
                               dispatch_context=({'current_epoch': 1, 'baseline': order(1)}
                                                 if dispatch is None else dispatch))


def reject(api, call, private=()):
    recorded = []
    for _ in range(2):
        with pytest.raises(api.ActionError) as caught:
            call()
        error = caught.value
        assert isinstance(error.path, tuple) and error.message
        for value in private:
            assert value not in str(error) and value not in repr(error)
        assert error.__context__ is None or error.__suppress_context__
        recorded.append((error.path, error.message))
    assert recorded[0] == recorded[1]


def changed(data, path, value):
    data = deepcopy(data)
    target = data
    for k in path[:-1]:
        target = target[k]
    target[path[-1]] = value
    return data
