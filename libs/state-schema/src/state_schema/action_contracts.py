"""REQ-018 pure action contracts; shape factories are not trusted completion.

Contextual helpers revalidate explicit inventory/catalogue and trusted caller
inputs. No helper authenticates, dispatches, allocates IDs or observes a clock.
Frozen records keep nested JSON as private immutable text; snapshots are fresh.
Direct constructors are internal typed records, not external validation seams.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import cast

from .canonical_state import DeviceState, Ordering, StateError, evaluate_convergence
from .capability import CapabilityCatalogue, CapabilityDescriptor, CapabilityError, CompletionPolicy
from .home_inventory import CANONICAL_ID_PATTERN, ErrorPath, Inventory, InventoryError

_TOKEN = re.compile(r"[A-Za-z0-9._:-]{1,128}", re.ASCII)
_CAPABILITY = re.compile(r"[a-z][a-z0-9_]{0,31}(\.[a-z][a-z0-9_]{0,31}){1,3}", re.ASCII)
_MEMBER = re.compile(r"[a-z][a-z0-9_]{0,63}", re.ASCII)
_IDENTITY = ('home_id', 'device_id', 'capability_id', 'capability_version', 'action_id')
_STATES = ('accepted', 'running', 'acknowledged', 'succeeded', 'failed', 'timed_out', 'cancelled')
_EDGES = {
    'accepted': ('running', 'failed', 'timed_out', 'cancelled'),
    'running': ('acknowledged', 'succeeded', 'failed', 'timed_out', 'cancelled'),
}


class ActionError(ValueError):
    """Fixed diagnostic location/reason without supplied keys or values."""

    def __init__(self, path: ErrorPath, message: str) -> None:
        self.path = path
        self.message = message
        location = '$' + ''.join(f'[{p}]' if isinstance(p, int) else f'.{p}' for p in path)
        super().__init__(f'{location}: {message}')


def _map(value: object, path: ErrorPath = ()) -> dict[str, object]:
    if type(value) is not dict or any(type(k) is not str for k in value):
        raise ActionError(path, 'expected an object with string field names')
    return cast(dict[str, object], value)


def _object(value: object, fields: tuple[str, ...], path: ErrorPath = ()) -> dict[str, object]:
    data = _map(value, path)
    for field in fields:
        if field not in data:
            raise ActionError((*path, field), 'required field is missing')
    if data.keys() - set(fields):
        raise ActionError((*path, '<unknown>'), 'unknown structural field')
    return data


def _integer(value: object, path: ErrorPath, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ActionError(path, 'expected an integer within declared bounds')
    return value


def _version(value: object, path: ErrorPath) -> int:
    if _integer(value, path, 1) != 1:
        raise ActionError(path, 'unsupported schema version')
    return 1


def _name(value: object, path: ErrorPath, pattern: re.Pattern[str] = _TOKEN) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ActionError(path, 'invalid contract identifier')
    return value


def _choice(value: object, path: ErrorPath, choices: tuple[str, ...]) -> str:
    if type(value) is not str or value not in choices:
        raise ActionError(path, 'unsupported contract value')
    return value


def _text(value: object, path: ErrorPath) -> str:
    if type(value) is not str or not value.strip() or len(value) > 256:
        raise ActionError(path, 'expected nonblank text of at most 256 characters')
    return value


def _snapshot(value: object, path: ErrorPath, depth: int = 1,
              active: frozenset[int] = frozenset()) -> object:
    if depth > 16:
        raise ActionError(path, 'JSON depth exceeds 16')
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ActionError(path, 'expected a finite JSON number')
        return value
    if type(value) not in (dict, list):
        raise ActionError(path, 'expected a strict JSON value')
    if id(value) in active:
        raise ActionError(path, 'cyclic JSON value')
    active = active | {id(value)}
    if type(value) is list:
        return [_snapshot(v, (*path, i), depth + 1, active)
                for i, v in enumerate(cast(list[object], value))]
    return {k: _snapshot(v, (*path, '<property>'), depth + 1, active)
            for k, v in _map(value, path).items()}


def _encode(value: object, path: ErrorPath) -> str:
    snapshot = _snapshot(value, path)
    try:
        return json.dumps(snapshot, ensure_ascii=True, allow_nan=False,
                          sort_keys=True, separators=(',', ':'))
    except (ValueError, OverflowError, RecursionError):
        raise ActionError(path, 'JSON value cannot be represented') from None


def _decode(value: str) -> object:
    return cast(object, json.loads(value))


def _same(left: object, right: object) -> bool:
    """Type-exact equality, deliberately independent of Capability enum equality."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same(v, right[k]) for k, v in left.items())
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return bool(left == right)


@dataclass(frozen=True, slots=True)
class _Identity:
    home_id: str
    device_id: str
    capability_id: str
    capability_version: int
    action_id: str

    @classmethod
    def parse(cls, data: dict[str, object], path: ErrorPath = ()) -> _Identity:
        return cls(
            _name(data['home_id'], (*path, 'home_id'), CANONICAL_ID_PATTERN),
            _name(data['device_id'], (*path, 'device_id'), CANONICAL_ID_PATTERN),
            _name(data['capability_id'], (*path, 'capability_id'), _CAPABILITY),
            _integer(data['capability_version'], (*path, 'capability_version'), 1),
            _name(data['action_id'], (*path, 'action_id'), _MEMBER),
        )

    def to_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in _IDENTITY}


@dataclass(frozen=True, slots=True)
class RequesterContext:
    subject_id: str
    family_member_id: str
    home_id: str
    role: str

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> RequesterContext:
        d = _object(value, ('subject_id', 'family_member_id', 'home_id', 'role'), path)
        return cls(_text(d['subject_id'], (*path, 'subject_id')),
                   _text(d['family_member_id'], (*path, 'family_member_id')),
                   _name(d['home_id'], (*path, 'home_id'), CANONICAL_ID_PATTERN),
                   _choice(d['role'], (*path, 'role'), ('admin', 'adult', 'kid')))

    def to_dict(self) -> dict[str, object]:
        return {'subject_id': self.subject_id, 'family_member_id': self.family_member_id,
                'home_id': self.home_id, 'role': self.role}


@dataclass(frozen=True, slots=True)
class ActionRequest:
    schema_version: int
    identity: _Identity
    _arguments_json: str
    idempotency_key: str
    trace_id: str

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> ActionRequest:
        """Shape only: use validate_request/create_task at the admission boundary."""
        d = _object(value, ('schema_version', *_IDENTITY, 'arguments',
                            'idempotency_key', 'trace_id'), path)
        _map(d['arguments'], (*path, 'arguments'))
        return cls(_version(d['schema_version'], (*path, 'schema_version')),
                   _Identity.parse(d, path), _encode(d['arguments'], (*path, 'arguments')),
                   _name(d['idempotency_key'], (*path, 'idempotency_key')),
                   _name(d['trace_id'], (*path, 'trace_id')))

    @property
    def arguments(self) -> dict[str, object]:
        return cast(dict[str, object], _decode(self._arguments_json))

    def to_dict(self) -> dict[str, object]:
        return {'schema_version': self.schema_version, **self.identity.to_dict(),
                'arguments': self.arguments, 'idempotency_key': self.idempotency_key,
                'trace_id': self.trace_id}


@dataclass(frozen=True, slots=True)
class _Dispatch:
    current_epoch: int
    baseline: Ordering | None

    @classmethod
    def parse(cls, value: object) -> _Dispatch:
        d = _object(value, ('current_epoch', 'baseline'), ('dispatch_context',))
        epoch = _integer(d['current_epoch'], ('dispatch_context', 'current_epoch'))
        try:
            baseline = None if d['baseline'] is None else Ordering.from_dict(d['baseline'])
        except StateError:
            raise ActionError(
                ('dispatch_context', 'baseline'), 'invalid ordering baseline') from None
        return cls(epoch, baseline)

    def to_dict(self) -> dict[str, object]:
        return {'current_epoch': self.current_epoch,
                'baseline': None if self.baseline is None else self.baseline.to_dict()}


def _evidence(value: object) -> str:
    if value is None:
        return 'null'
    d = _map(value, ('evidence',))
    kind = _choice(d.get('kind'), ('evidence', 'kind'), ('ack', 'event', 'state'))
    extras = {'ack': (), 'event': ('event', 'payload', 'ordering'), 'state': ('state',)}[kind]
    _object(d, ('kind', 'task_id', 'trace_id', *_IDENTITY, *extras), ('evidence',))
    _name(d['task_id'], ('evidence', 'task_id'))
    _name(d['trace_id'], ('evidence', 'trace_id'))
    _Identity.parse(d, ('evidence',))
    if kind == 'event':
        _name(d['event'], ('evidence', 'event'), _MEMBER)
        try:
            Ordering.from_dict(d['ordering'])
        except StateError:
            raise ActionError(('evidence', 'ordering'), 'invalid event ordering') from None
    if kind == 'state':
        try:
            DeviceState.from_dict(d['state'])
        except StateError:
            raise ActionError(('evidence', 'state'), 'invalid canonical State evidence') from None
    return _encode(d, ('evidence',))


@dataclass(frozen=True, slots=True)
class ActionResult:
    schema_version: int
    task_id: str
    trace_id: str
    identity: _Identity
    state: str
    _output_json: str
    error_code: str | None
    _evidence_json: str
    physical_outcome: str

    @classmethod
    def from_dict(cls, value: object, path: ErrorPath = ()) -> ActionResult:
        """Shape only; a succeeded label does not prove trusted completion."""
        d = _object(value, ('schema_version', 'task_id', 'trace_id', *_IDENTITY,
                            'state', 'output', 'error', 'evidence', 'physical_outcome'), path)
        state = _choice(d['state'], (*path, 'state'), _STATES)
        out = _object(d['output'], ('present', 'value'), (*path, 'output'))
        if type(out['present']) is not bool:
            raise ActionError((*path, 'output', 'present'), 'expected a boolean')
        if not out['present'] and out['value'] is not None:
            raise ActionError((*path, 'output'), 'absent output requires null value')
        error = None
        if state in ('failed', 'timed_out'):
            error = _name(_object(d['error'], ('code',), (*path, 'error'))['code'],
                          (*path, 'error', 'code'))
        elif d['error'] is not None:
            raise ActionError((*path, 'error'), 'error is not allowed in this state')
        physical = _choice(d['physical_outcome'], (*path, 'physical_outcome'),
                           ('unverified', 'confirmed'))
        if physical != ('confirmed' if state == 'succeeded' else 'unverified'):
            raise ActionError((*path, 'physical_outcome'), 'outcome conflicts with state')
        ev = _evidence(d['evidence'])
        e = _decode(ev)
        kind = None if e is None else cast(dict[str, object], e)['kind']
        if state == 'accepted' and (out['present'] or e is not None):
            raise ActionError(path, 'accepted cannot carry execution output or evidence')
        if state == 'running' and kind not in (None, 'ack'):
            raise ActionError((*path, 'evidence'), 'running cannot carry success evidence')
        if state in ('failed', 'timed_out', 'cancelled') and e is not None:
            raise ActionError((*path, 'evidence'), 'failure or cancellation cannot carry evidence')
        if state == 'acknowledged' and kind != 'ack':
            raise ActionError((*path, 'evidence'), 'acknowledgement requires ACK evidence')
        if state == 'succeeded' and kind not in ('event', 'state'):
            raise ActionError((*path, 'evidence'), 'success requires completion evidence')
        return cls(_version(d['schema_version'], (*path, 'schema_version')),
                   _name(d['task_id'], (*path, 'task_id')),
                   _name(d['trace_id'], (*path, 'trace_id')), _Identity.parse(d, path),
                   state, _encode(out, (*path, 'output')), error, ev, physical)

    @property
    def output(self) -> dict[str, object]:
        return cast(dict[str, object], _decode(self._output_json))

    @property
    def evidence(self) -> dict[str, object] | None:
        return cast(dict[str, object] | None, _decode(self._evidence_json))

    def to_dict(self) -> dict[str, object]:
        return {'schema_version': self.schema_version, 'task_id': self.task_id,
                'trace_id': self.trace_id, **self.identity.to_dict(), 'state': self.state,
                'output': self.output,
                'error': None if self.error_code is None else {'code': self.error_code},
                'evidence': self.evidence, 'physical_outcome': self.physical_outcome}


@dataclass(frozen=True, slots=True)
class Task:
    schema_version: int
    task_id: str
    trace_id: str
    request: ActionRequest
    requester: RequesterContext
    completion_policy: CompletionPolicy
    state: str
    dispatch_context: _Dispatch | None
    result: ActionResult | None

    @classmethod
    def from_dict(cls, value: object) -> Task:
        """Shape only: use validate_task for contextual policy/evidence validation."""
        d = _object(value, ('schema_version', 'task_id', 'trace_id', 'request', 'requester',
                            'completion_policy', 'state', 'dispatch_context', 'result'))
        try:
            policy = CompletionPolicy.from_dict(d['completion_policy'])
        except CapabilityError:
            raise ActionError(('completion_policy',), 'invalid completion policy') from None
        state = _choice(d['state'], ('state',), _STATES)
        dispatch = None if d['dispatch_context'] is None else _Dispatch.parse(d['dispatch_context'])
        result = None if d['result'] is None else ActionResult.from_dict(d['result'], ('result',))
        if state == 'accepted' and dispatch is not None:
            raise ActionError(('dispatch_context',), 'accepted has no dispatch context')
        if state == 'running' and dispatch is None:
            raise ActionError(('dispatch_context',), 'running requires explicit dispatch context')
        if state not in ('accepted', 'running') and result is None:
            raise ActionError(('result',), 'terminal task requires a result')
        if result is not None and result.state != state:
            raise ActionError(('result', 'state'), 'result state conflicts with task')
        return cls(_version(d['schema_version'], ('schema_version',)),
                   _name(d['task_id'], ('task_id',)), _name(d['trace_id'], ('trace_id',)),
                   ActionRequest.from_dict(d['request'], ('request',)),
                   RequesterContext.from_dict(d['requester'], ('requester',)),
                   policy, state, dispatch, result)

    def to_dict(self) -> dict[str, object]:
        return {'schema_version': self.schema_version, 'task_id': self.task_id,
                'trace_id': self.trace_id, 'request': self.request.to_dict(),
                'requester': self.requester.to_dict(),
                'completion_policy': self.completion_policy.to_dict(), 'state': self.state,
                'dispatch_context': (None if self.dispatch_context is None
                                     else self.dispatch_context.to_dict()),
                'result': None if self.result is None else self.result.to_dict()}


def _selected(request: ActionRequest, requester: RequesterContext, inventory: object,
              catalogue: object) -> CapabilityDescriptor:
    if request.identity.home_id != requester.home_id:
        raise ActionError(('requester', 'home_id'), 'requester Home conflicts with Request')
    try:
        inv = Inventory.from_dict(inventory)
    except InventoryError:
        raise ActionError(('inventory',), 'invalid canonical inventory') from None
    identity = request.identity
    if inv.home.id != identity.home_id or not any(d.id == identity.device_id for d in inv.devices):
        raise ActionError(('device_id',), 'Device does not belong to Request Home')
    try:
        cat = CapabilityCatalogue.from_dict(catalogue)
        descriptor = cat.get(identity.capability_id, identity.capability_version)
        descriptor.validate_payload('action_input', identity.action_id, request.arguments)
    except CapabilityError:
        raise ActionError(('arguments',), 'invalid capability selection or action input') from None
    return descriptor


def validate_request(data: object, *, requester: object, inventory: object,
                     catalogue: object) -> dict[str, object]:
    """Validate explicit trusted context; does not authenticate or grant permission."""
    request = ActionRequest.from_dict(data)
    context = RequesterContext.from_dict(requester, ('requester',))
    _selected(request, context, inventory, catalogue)
    return request.to_dict()


def _correlation(e: dict[str, object], task: Task, path: ErrorPath) -> None:
    expected = {'task_id': task.task_id, 'trace_id': task.trace_id,
                **task.request.identity.to_dict()}
    if any(not _same(e[k], v) for k, v in expected.items()):
        raise ActionError(path, 'evidence or result correlation mismatch')


def _check_result(result: ActionResult, task: Task, descriptor: CapabilityDescriptor) -> None:
    _correlation(result.to_dict(), task, ('result',))
    identity = task.request.identity
    if result.output['present']:
        try:
            descriptor.validate_payload('action_output', identity.action_id, result.output['value'])
        except CapabilityError:
            raise ActionError(('output', 'value'), 'invalid action output') from None
    e = result.evidence
    if e is not None:
        _correlation(e, task, ('evidence',))
    policy = task.completion_policy
    if result.state == 'acknowledged':
        if policy.kind != 'ack_only' or task.dispatch_context is None:
            raise ActionError(('state',), 'acknowledgement requires running ack-only policy')
    if result.state != 'succeeded':
        return
    if e is None or policy.kind == 'ack_only':
        raise ActionError(('evidence',), 'ACK cannot confirm physical success')
    dispatch = task.dispatch_context
    if dispatch is None or dispatch.baseline is None:
        raise ActionError(('dispatch_context',), 'success requires a dispatch baseline')
    baseline = dispatch.baseline
    if baseline.epoch != dispatch.current_epoch:
        raise ActionError(('dispatch_context', 'baseline'), 'baseline is not current generation')
    if policy.kind == 'event_confirmed':
        if e['kind'] != 'event' or e['event'] != policy.event:
            raise ActionError(('evidence',), 'declared event evidence is required')
        try:
            descriptor.validate_payload('event', e['event'], e['payload'])
            ordering = Ordering.from_dict(e['ordering'])
        except (CapabilityError, StateError):
            raise ActionError(('evidence',), 'invalid declared event payload or ordering') from None
        if ordering.epoch != dispatch.current_epoch or ordering <= baseline:
            raise ActionError(
                ('evidence', 'ordering'), 'event is not current post-baseline evidence')
        return
    if e['kind'] != 'state':
        raise ActionError(('evidence',), 'canonical State evidence is required')
    try:
        state = DeviceState.from_dict(e['state'])
        if state.home_id != identity.home_id or state.device_id != identity.device_id:
            raise ActionError(('evidence', 'state'), 'State identity mismatch')
        targets: dict[str, object] = {}
        reports = dict(state.reported_state)
        arguments = task.request.arguments
        for name, source in policy.targets:
            value = arguments[cast(str, source.field)] if source.source == 'input' else source.value
            targets[name] = descriptor.validate_payload('property', name, value)
            report = reports.get(name)
            if report is not None and report.status == 'known':
                descriptor.validate_payload('property', name, report.value)
        snapshot = state.to_dict()
        # Never trust submitted desired_state to choose targets or rebase dispatch.
        snapshot['desired_state'] = {'revision': 1, 'values': targets,
                                     'report_baseline': baseline.to_dict()}
        convergence = evaluate_convergence(snapshot, current_epoch=dispatch.current_epoch)
    except (CapabilityError, StateError):
        raise ActionError(
            ('evidence', 'state'), 'invalid canonical completion observations') from None
    if convergence != 'confirmed':
        raise ActionError(('evidence', 'state'), 'State has not confirmed every target')


def _validated_task(data: object, inventory: object,
                    catalogue: object) -> tuple[Task, CapabilityDescriptor]:
    task = Task.from_dict(data)
    descriptor = _selected(task.request, task.requester, inventory, catalogue)
    if task.trace_id != task.request.trace_id:
        raise ActionError(('trace_id',), 'Task trace conflicts with Request')
    action = dict(descriptor.actions)[task.request.identity.action_id]
    if not _same(task.completion_policy.to_dict(), action.completion_policy.to_dict()):
        raise ActionError(('completion_policy',), 'Task policy conflicts with selected descriptor')
    if task.result is not None:
        _check_result(task.result, task, descriptor)
    return task, descriptor


def validate_task(data: object, *, inventory: object, catalogue: object) -> dict[str, object]:
    """Validate a trusted persisted Task snapshot, including contextual completion."""
    task, _ = _validated_task(data, inventory, catalogue)
    return task.to_dict()


def validate_result(data: object, *, task: object, inventory: object,
                    catalogue: object) -> dict[str, object]:
    """Validate correlation/output/evidence; transition legality is checked separately."""
    record, descriptor = _validated_task(task, inventory, catalogue)
    result = ActionResult.from_dict(data)
    _check_result(result, record, descriptor)
    return result.to_dict()


def create_task(data: object, *, requester: object, task_id: object, inventory: object,
                catalogue: object) -> dict[str, object]:
    request = ActionRequest.from_dict(data)
    context = RequesterContext.from_dict(requester, ('requester',))
    descriptor = _selected(request, context, inventory, catalogue)
    policy = dict(descriptor.actions)[request.identity.action_id].completion_policy
    return Task(1, _name(task_id, ('task_id',)), request.trace_id, request, context,
                policy, 'accepted', None, None).to_dict()


def transition_task(data: object, result: object, *, inventory: object,
                    catalogue: object, dispatch_context: object = None) -> dict[str, object]:
    task, descriptor = _validated_task(data, inventory, catalogue)
    out = ActionResult.from_dict(result)
    _correlation(out.to_dict(), task, ('result',))
    if out.state == task.state:
        if dispatch_context is not None:
            raise ActionError(('dispatch_context',), 'dispatch context cannot change on replay')
        # Initial accepted Tasks have no Result; an empty accepted Result is a no-op.
        if task.result is None and task.state == 'accepted':
            _check_result(out, task, descriptor)
            return task.to_dict()
        if task.result is None or not _same(task.result.to_dict(), out.to_dict()):
            raise ActionError(('result',), 'conflicting same-state result')
        return task.to_dict()
    if out.state not in _EDGES.get(task.state, ()):
        raise ActionError(('state',), 'invalid task transition')
    dispatch = task.dispatch_context
    if task.state == 'accepted' and out.state == 'running':
        dispatch = _Dispatch.parse(dispatch_context)
    elif dispatch_context is not None:
        raise ActionError(('dispatch_context',), 'dispatch context cannot be overridden')
    candidate = Task(1, task.task_id, task.trace_id, task.request, task.requester,
                     task.completion_policy, out.state, dispatch, out)
    _check_result(out, candidate, descriptor)
    return candidate.to_dict()


def compare_idempotency(data: object, request: object, *, requester: object,
                        inventory: object, catalogue: object) -> str:
    """Classify only: replay retains the existing Task; no allocation/store/dispatch."""
    task, _ = _validated_task(data, inventory, catalogue)
    incoming = ActionRequest.from_dict(request)
    context = RequesterContext.from_dict(requester, ('requester',))
    _selected(incoming, context, inventory, catalogue)
    previous_scope = (task.requester.home_id, task.requester.family_member_id,
                      task.requester.subject_id, task.request.idempotency_key)
    incoming_scope = (context.home_id, context.family_member_id, context.subject_id,
                      incoming.idempotency_key)
    if previous_scope != incoming_scope:
        return 'distinct'
    if (task.request.identity == incoming.identity
            and _same(task.request.arguments, incoming.arguments)):
        return 'replay'
    return 'conflict'
