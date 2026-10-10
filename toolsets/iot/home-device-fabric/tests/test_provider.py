"""REQ-019 TCs assert actual shared-helper integration and provider effects."""

from copy import deepcopy

import pytest
from fixtures import (
    binding,
    config,
    correlation,
    delivery,
    evidence,
    input_record,
    outcome,
    request,
    requester,
    result,
    script,
    task,
)
from state_schema import action_contracts as actions
from state_schema.canonical_state import apply_state_update


def runtime():
    from home_device_fabric import MockProvider, ProviderProtocol
    from state_schema.provider_contracts import (
        MockConfiguration,
        NormalizedInput,
        ProviderError,
        ProviderOutcome,
    )

    return (
        MockProvider,
        ProviderProtocol,
        MockConfiguration,
        NormalizedInput,
        ProviderOutcome,
        ProviderError,
    )


def provider(c=None):
    return runtime()[0](config() if c is None else c)


def reject(call, code=None):
    error = runtime()[-1]
    with pytest.raises(error) as caught:
        call()
    e = caught.value
    assert isinstance(e.path, tuple)
    assert e.message and e.code
    assert e.__context__ is None or e.__suppress_context__
    if code:
        assert e.code == code
    return e


# TC-019-01: strict admission and discovery.
@pytest.mark.parametrize("field", list(config()))
@pytest.mark.tc019_01
def test_config_required_fields(field):
    c = config()
    del c[field]
    reject(lambda: provider(c))


@pytest.mark.parametrize("version", [True, False, 0, 2, 1.0, "1", None])
@pytest.mark.tc019_01
def test_config_version(version):
    c = config()
    c["schema_version"] = version
    reject(lambda: provider(c))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object(), (1,), {1: "private"}])
@pytest.mark.tc019_01
def test_strict_json(value):
    c = config()
    c["private-extra"] = value
    e = reject(lambda: provider(c))
    assert "private-extra" not in str(e)


@pytest.mark.tc019_01
def test_cycles_safe_errors():
    c = config()
    c["cycle"] = c
    assert reject(lambda: provider(c)).code == "invalid_json"
    c = config()
    c["inventory"]["home"]["id"] = "secret://private.endpoint"
    e = reject(lambda: provider(c))
    assert "secret" not in str(e) and "endpoint" not in repr(e)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "unknown",
        "foreign",
        "missing_binding",
        "foreign_instance",
        "extra_binding",
        "undeclared_revision",
        "duplicate_support",
        "device_key",
        "ambiguous_property",
    ],
)
@pytest.mark.tc019_01
def test_registration_integrity(mutation):
    c = config()
    d = c["devices"][0]
    if mutation == "duplicate":
        c["devices"].append(deepcopy(d))
    if mutation == "unknown":
        d["device_id"] = "device-unknown"
    if mutation == "foreign":
        d["home_id"] = "home-other"
    if mutation == "missing_binding":
        c["bindings"]["bindings"] = []
    if mutation == "foreign_instance":
        c["bindings"]["bindings"][0]["provider_instance_id"] = "mock-other"
    if mutation == "extra_binding":
        c["devices"] = []
    if mutation == "undeclared_revision":
        d["supported_capabilities"][0]["capability_version"] = 2
    if mutation == "duplicate_support":
        d["supported_capabilities"] *= 2
    if mutation == "device_key":
        d["device_key"] = "private"
    if mutation == "ambiguous_property":
        desc = deepcopy(c["catalogue"]["capabilities"][0])
        desc["capability_id"] = "demo.duplicate"
        # Use a descriptor with the same supported switch property.
        desc = deepcopy(
            next(
                x for x in c["catalogue"]["capabilities"] if x["capability_id"] == "home.switchable"
            )
        )
        desc["capability_id"] = "demo.duplicate"
        c["catalogue"]["capabilities"].append(desc)
        d["supported_capabilities"].append(
            {"capability_id": "demo.duplicate", "capability_version": 1}
        )
    reject(lambda: provider(c))


@pytest.mark.tc019_01
def test_discovery_detached_and_protocol():
    c = config()
    p = provider(c)
    assert isinstance(p, runtime()[1])
    d = p.discover()[0]
    assert d.to_dict()["binding"] == binding()
    c["devices"].clear()
    c["bindings"]["bindings"].clear()
    raw = d.to_dict()
    raw["binding"]["mapping"]["device_key"] = "changed"
    assert p.discover()[0].to_dict()["binding"] == binding()
    state = p.snapshot()[0].to_dict()
    assert state["desired_state"] is None and state["reported_state"] == {}
    assert state["availability"]["status"] == "unknown"
    state["availability"]["status"] = "online"
    assert p.snapshot()[0].availability.status == "unknown"


# TC-019-02: supported observations/events, State and ordering.
@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "ha"),
        ("provider_instance_id", "mock-other"),
        ("home_id", "home-other"),
        ("device_id", "device-other"),
        ("capability_id", "home.positionable"),
        ("capability_version", 2),
        ("member", "private-unknown"),
        ("schema_version", True),
    ],
)
@pytest.mark.tc019_02
def test_input_context(field, value):
    c = config()
    t = task(c)
    i = input_record()
    i[field] = value
    script(c, t, [delivery(0, i)])
    reject(lambda: provider(c))


@pytest.mark.parametrize("value", [0, 1, "false", None, 1.5])
@pytest.mark.tc019_02
def test_boolean_property_types(value):
    c = config()
    t = task(c)
    script(c, t, [delivery(0, input_record(value=value))])
    reject(lambda: provider(c))


@pytest.mark.tc019_02
def test_fractional_position_rejected():
    c = config()
    c["devices"][0]["supported_capabilities"] = [
        {"capability_id": "home.positionable", "capability_version": 1}
    ]
    i = input_record(value=3.5)
    i.update(capability_id="home.positionable", member="position_percent")
    script(c, task(config()), [delivery(0, i)])
    reject(lambda: provider(c))


@pytest.mark.tc019_02
def test_unknown_offline_and_ordering():
    c = config()
    t = task(c)
    unknown = input_record()
    unknown["payload"] = {"status": "unknown", "value": None, "observed_at": None, "ordering": None}
    off = input_record("availability")
    off["payload"]["status"] = "offline"
    script(
        c,
        t,
        [
            delivery(0, unknown),
            delivery(1, off),
            delivery(2, input_record(value=False)),
            delivery(3, input_record(sequence=1, value=True)),
            delivery(4, input_record(sequence=100, value=True, epoch=0)),
        ],
    )
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    assert list(p.advance(0))[0].input.to_dict()["payload"]["status"] == "unknown"
    list(p.advance(4))
    s = p.snapshot()[0].to_dict()
    assert s["availability"]["status"] == "offline"
    assert s["reported_state"]["is_on"]["value"] is False
    assert s["reported_state"]["is_on"]["ordering"] == {"epoch": 1, "sequence": 2}
    assert p.snapshot()[0].to_dict() == s


@pytest.mark.tc019_02
def test_initial_catalogue_has_no_events():
    c = config()
    t = task(c)
    i = input_record("event")
    i.update(member="changed", payload={"value": {}, "ordering": {"epoch": 1, "sequence": 2}})
    script(c, t, [delivery(0, i)])
    reject(lambda: provider(c))


# TC-019-03: guarded submission, correlated ACK, shared completion helpers.
@pytest.mark.parametrize(
    "mutation",
    [
        "accepted",
        "terminal",
        "arguments",
        "policy",
        "trace",
        "binding",
        "support",
        "attempt",
        "correlation",
    ],
)
@pytest.mark.tc019_03
def test_submit_rejects_before_effects(mutation):
    c = config()
    t = task(c)
    selected = binding()
    attempt = "attempt-1"
    o = outcome(t)
    script(c, t, [delivery(0, o, True)])
    if mutation == "support":
        c["devices"][0]["supported_capabilities"] = []
    if mutation == "correlation":
        o["result"]["trace_id"] = "trace-other"
    p = provider(c)
    if mutation == "accepted":
        t = actions.create_task(
            request(),
            requester=requester(),
            task_id="task-1",
            inventory=c["inventory"],
            catalogue=c["catalogue"],
        )
    if mutation == "terminal":
        t = actions.transition_task(
            t, result(t, "cancelled"), inventory=c["inventory"], catalogue=c["catalogue"]
        )
    if mutation == "arguments":
        t["request"]["arguments"]["is_on"] = 1
    if mutation == "policy":
        t["completion_policy"] = {"kind": "ack_only"}
    if mutation == "trace":
        t["trace_id"] = "trace-other"
    if mutation == "binding":
        selected["mapping"]["device_key"] = "other"
    if mutation == "attempt":
        attempt = "attempt-missing"
    reject(lambda: p.submit(t, binding=selected, attempt_id=attempt))
    assert p.dispatch_log == () and p.delivery_log == ()
    assert list(p.advance(100000)) == []


def completion_run(c, t, end):
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    state = p.snapshot()[0].to_dict()
    times = []
    for item in p.advance(end):
        times.append(item.time_ms)
        if item.outcome:
            r = item.outcome.to_dict()["result"]
            if t["state"] == "running" and r["state"] == "running":
                actions.validate_result(
                    r, task=t, inventory=c["inventory"], catalogue=c["catalogue"]
                )
            elif t["state"] == "running":
                t = actions.transition_task(
                    t, r, inventory=c["inventory"], catalogue=c["catalogue"]
                )
        if item.input:
            i = item.input.to_dict()
            state = apply_state_update(
                state,
                current_epoch=1,
                reported_state={i["member"]: i["payload"]} if i["kind"] == "property" else None,
                availability=i["payload"] if i["kind"] == "availability" else None,
            )
            if t["state"] == "running" and i["correlation"]:
                e = evidence(t, "state")
                e["state"] = state
                try:
                    t = actions.transition_task(
                        t,
                        result(t, "succeeded", e),
                        inventory=c["inventory"],
                        catalogue=c["catalogue"],
                    )
                except actions.ActionError:
                    pass
        if t["state"] != "running":
            p.settle(t)
    return p, t, state, times


def convergence_script(c, t, due=10):
    return script(
        c,
        t,
        [
            delivery(0, outcome(t), True),
            delivery(due, input_record("availability")),
            delivery(due, input_record(correlated=correlation(t))),
        ],
    )


@pytest.mark.tc019_03
def test_real_convergence_across_large_jump():
    c = config()
    t = task(c)
    convergence_script(c, t)
    p, t, state, times = completion_run(c, t, 100000)
    assert t["state"] == "succeeded" and t["result"]["physical_outcome"] == "confirmed"
    assert state["reported_state"]["is_on"]["value"] is False
    assert times == [0, 10, 10] and p.now_ms == 100000
    assert list(p.advance(100000)) == []
    assert len(p.dispatch_log) == 1


@pytest.mark.tc019_03
def test_null_baseline_and_ack_do_not_confirm():
    c = config()
    t = task(c, baseline=False)
    convergence_script(c, t)
    p, t, _, _ = completion_run(c, t, 100000)
    assert t["state"] == "timed_out" and t["result"]["physical_outcome"] == "unverified"
    assert len(p.dispatch_log) == 1


# TC-019-04: explicit chronological virtual time and terminal suppression.
@pytest.mark.parametrize("offset", [-1, 0, 1])
@pytest.mark.tc019_04
def test_deadline_order(offset):
    c = config()
    t = task(c)
    desc = next(
        x for x in c["catalogue"]["capabilities"] if x["capability_id"] == "home.switchable"
    )
    deadline = desc["actions"]["set_on"]["timeout_ms"]
    convergence_script(c, t, deadline + offset)
    _, t, _, times = completion_run(c, t, deadline + 2)
    assert t["state"] == ("succeeded" if offset < 0 else "timed_out")
    assert times == sorted(times)


@pytest.mark.parametrize("now", [True, False, -1, 1.0, "1", None])
@pytest.mark.tc019_04
def test_invalid_virtual_time(now):
    p = provider()
    reject(lambda: list(p.advance(now)), "invalid_time")
    assert p.now_ms == 0


@pytest.mark.tc019_04
def test_clock_backwards_and_iteration_close():
    c = config()
    t = task(c)
    script(c, t, [delivery(2, input_record()), delivery(4, input_record(sequence=3))])
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    iterator = p.advance(6)
    assert next(iterator).time_ms == 2
    reject(lambda: list(p.advance(6)), "advance_in_progress")
    reject(lambda: p.submit(t, binding=binding(), attempt_id="attempt-1"), "advance_in_progress")
    iterator.close()
    assert p.now_ms == 2
    assert [i.time_ms for i in p.advance(6)] == [4]
    reject(lambda: list(p.advance(5)), "invalid_time")


@pytest.mark.tc019_04
def test_failure_after_ack_is_unverified():
    c = config()
    t = task(c)
    script(c, t, [delivery(0, outcome(t), True), delivery(2, outcome(t, "failed"), True)])
    _, t, _, times = completion_run(c, t, 100000)
    assert times == [0, 2] and t["state"] == "failed"
    assert t["result"]["physical_outcome"] == "unverified"


@pytest.mark.tc019_04
def test_cancel_preserves_independent_inputs_and_consumed_observation():
    c = config()
    t = task(c)
    script(
        c,
        t,
        [
            delivery(0, input_record()),
            delivery(1, input_record(sequence=3, correlated=correlation(t))),
            delivery(2, outcome(t, "failed"), True),
            delivery(3, input_record(sequence=4, value=True)),
        ],
    )
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    list(p.advance(0))
    cancelled = actions.transition_task(
        t, result(t, "cancelled"), inventory=c["inventory"], catalogue=c["catalogue"]
    )
    p.settle(cancelled)
    assert p.snapshot()[0].to_dict()["reported_state"]["is_on"]["value"] is False
    assert [i.time_ms for i in p.advance(100000)] == [3]
    assert p.snapshot()[0].to_dict()["reported_state"]["is_on"]["value"] is True


@pytest.mark.tc019_04
def test_settlement_must_match_frozen_task():
    c = config()
    t = task(c)
    script(c, t)
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    cancelled = actions.transition_task(
        t, result(t, "cancelled"), inventory=c["inventory"], catalogue=c["catalogue"]
    )
    cancelled["request"]["trace_id"] = "trace-other"
    cancelled["trace_id"] = "trace-other"
    cancelled["result"]["trace_id"] = "trace-other"
    reject(lambda: p.settle(cancelled), "invalid_settlement")
    assert len(list(p.advance(100000))) == 1


# TC-019-05: explicit scripts and real scoped replay classification.
@pytest.mark.parametrize("conflict", [False, True])
@pytest.mark.tc019_05
def test_caller_replay_conflict_no_submission(conflict):
    c = config()
    t = task(c)
    script(c, t)
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    r = request()
    r["trace_id"] = "trace-new"
    if conflict:
        r["arguments"]["is_on"] = True
    verdict = actions.compare_idempotency(
        t, r, requester=requester(), inventory=c["inventory"], catalogue=c["catalogue"]
    )
    assert verdict == ("conflict" if conflict else "replay")
    assert t["task_id"] == "task-1" and t["trace_id"] == "trace-1"
    assert len(p.dispatch_log) == 1
    reject(lambda: p.submit(t, binding=binding(), attempt_id="attempt-1"))
    assert len(p.dispatch_log) == 1


@pytest.mark.tc019_05
def test_explicit_second_attempt_no_automatic_retry():
    c = config()
    first = task(c)
    second = task(c, task_id="task-2")
    script(c, first)
    script(c, second, attempt="attempt-2")
    p = provider(c)
    p.submit(first, binding=binding(), attempt_id="attempt-1")
    items = list(p.advance(100000))
    assert len(items) == 1
    assert len(p.dispatch_log) == 1
    p.submit(second, binding=binding(), attempt_id="attempt-2")
    assert len(p.dispatch_log) == 2
    assert len(list(p.advance(200000))) == 1


# TC-019-06: mutable input/result isolation and deterministic behavior.
@pytest.mark.tc019_06
def test_determinism_and_logs_isolated():
    c = config()
    t = task(c)
    convergence_script(c, t)
    p = provider(c)
    q = provider(deepcopy(c))
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    q.submit(deepcopy(t), binding=binding(), attempt_id="attempt-1")
    c["scenarios"].clear()
    t["request"]["arguments"]["is_on"] = True
    a = [i.to_dict() for i in p.advance(100000)]
    b = [i.to_dict() for i in q.advance(100000)]
    assert a == b and p.dispatch_log == q.dispatch_log and p.delivery_log == q.delivery_log
    log = p.dispatch_log[0]
    log["task_id"] = "changed"
    record = p.delivery_log[0]
    record["time_ms"] = -1
    assert p.dispatch_log == q.dispatch_log and p.delivery_log == q.delivery_log
    a[0]["outcome"]["result"]["trace_id"] = "changed"
    assert p.delivery_log == q.delivery_log


@pytest.mark.parametrize("field", ["schema_version", "provider", "provider_instance_id", "result"])
@pytest.mark.tc019_06
def test_outcome_required_fields(field):
    c = config()
    t = task(c)
    o = outcome(t)
    del o[field]
    script(c, t, [delivery(0, o, True)])
    reject(lambda: provider(c))


@pytest.mark.parametrize("bad", ["duplicate", "negative", "both", "neither", "success", "extra"])
@pytest.mark.tc019_06
def test_scenario_admission(bad):
    c = config()
    t = task(c)
    d = delivery(0, outcome(t), True)
    script(c, t, [d])
    if bad == "duplicate":
        c["scenarios"] *= 2
    if bad == "negative":
        d["delay_ms"] = -1
    if bad == "both":
        d["input"] = input_record()
    if bad == "neither":
        d["outcome"] = None
    if bad == "success":
        d["outcome"]["result"] = result(t, "succeeded", evidence(t, "state"))
    if bad == "extra":
        c["scenarios"][0]["private-field"] = "private-value"
    reject(lambda: provider(c))


@pytest.mark.parametrize("member", [[], {}, True, 3, None])
@pytest.mark.tc019_06
def test_malformed_property_member_safe(member):
    c = config()
    t = task(c)
    i = input_record()
    i["member"] = member
    script(c, t, [delivery(0, i)])
    reject(lambda: provider(c))


def policy_config(kind):
    c = config()
    d = next(x for x in c["catalogue"]["capabilities"] if x["capability_id"] == "home.switchable")
    if kind == "ack_only":
        d["actions"]["set_on"]["completion_policy"] = {"kind": kind}
    else:
        d["events"] = {
            "changed": {
                "title": "Changed",
                "description": "Explicit fictional completion event",
                "data_schema": {
                    "type": "object",
                    "properties": {"is_on": {"type": "boolean"}},
                    "required": ["is_on"],
                    "additionalProperties": False,
                }
            }
        }
        d["actions"]["set_on"]["completion_policy"] = {"kind": kind, "event": "changed"}
    return c


@pytest.mark.tc019_03
def test_ack_only_is_acknowledged_not_success():
    c = policy_config("ack_only")
    t = task(c)
    script(c, t, [delivery(0, outcome(t, "acknowledged"), True)])
    p, t, _, times = completion_run(c, t, 100000)
    assert t["state"] == "acknowledged" and t["result"]["physical_outcome"] == "unverified"
    assert times == [0] and len(p.dispatch_log) == 1


@pytest.mark.parametrize("sequence,epoch,valid", [(2, 1, True), (1, 1, False), (2, 0, False)])
@pytest.mark.tc019_03
def test_declared_event_real_completion(sequence, epoch, valid):
    c = policy_config("event_confirmed")
    t = task(c)
    i = input_record("event", correlated=correlation(t))
    i.update(
        member="changed",
        payload={"value": {"is_on": False}, "ordering": {"epoch": epoch, "sequence": sequence}},
    )
    script(c, t, [delivery(3, i)])
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    states = []
    for item in p.advance(100000):
        if item.input:
            inp = item.input.to_dict()
            e = evidence(t, "event")
            e.update(
                event=inp["member"],
                payload=inp["payload"]["value"],
                ordering=inp["payload"]["ordering"],
            )
            if valid:
                t = actions.transition_task(
                    t, result(t, "succeeded", e), inventory=c["inventory"], catalogue=c["catalogue"]
                )
                p.settle(t)
            else:
                with pytest.raises(actions.ActionError):
                    actions.transition_task(
                        t,
                        result(t, "succeeded", e),
                        inventory=c["inventory"],
                        catalogue=c["catalogue"],
                    )
        else:
            t = actions.transition_task(
                t,
                item.outcome.to_dict()["result"],
                inventory=c["inventory"],
                catalogue=c["catalogue"],
            )
            p.settle(t)
        states.append(t["state"])
    assert t["state"] == ("succeeded" if valid else "timed_out")
    assert states == (["succeeded"] if valid else ["running", "timed_out"])


@pytest.mark.parametrize("alter", ["trace", "capability", "output"])
@pytest.mark.tc019_03
def test_outcome_context_rejects_all_before_effect(alter):
    c = config()
    t = task(c)
    o = outcome(t)
    if alter == "trace":
        o["result"]["trace_id"] = "trace-other"
    if alter == "capability":
        o["result"]["capability_id"] = "home.positionable"
    if alter == "output":
        o["result"]["output"] = {"present": True, "value": {"private": 1}}
    script(c, t, [delivery(0, o, True)])
    p = provider(c)
    reject(lambda: p.submit(t, binding=binding(), attempt_id="attempt-1"), "invalid_outcome")
    assert p.dispatch_log == () and list(p.advance(100000)) == []


@pytest.mark.tc019_03
def test_valid_null_output_is_present():
    c = config()
    t = task(c)
    o = outcome(t)
    o["result"]["output"] = {"present": True, "value": None}
    script(c, t, [delivery(0, o, True)])
    p = provider(c)
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    assert list(p.advance(0))[0].outcome.to_dict()["result"]["output"] == {
        "present": True,
        "value": None,
    }


@pytest.mark.tc019_06
def test_runtime_denies_file_environment_and_datetime(monkeypatch):
    import builtins
    import datetime
    import io
    import os
    from collections.abc import Mapping

    c = config()
    t = task(c)
    convergence_script(c, t)
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("ambient access forbidden")

    class DeniedEnvironment(Mapping):
        __getitem__ = deny
        __iter__ = deny
        __len__ = deny

    class DeniedDatetime(datetime.datetime):
        now = classmethod(deny)
        utcnow = classmethod(deny)
        today = classmethod(deny)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", deny)
        patch.setattr(os, "environ", DeniedEnvironment())
        patch.setattr(datetime, "datetime", DeniedDatetime)
        p = provider(c)
        p.submit(t, binding=binding(), attempt_id="attempt-1")
        for item in p.advance(100000):
            item.to_dict()
        p.snapshot()
        p.discover()
        p.dispatch_log
        p.delivery_log
    assert not attempts


@pytest.mark.tc019_01
def test_discovery_record_roundtrip_and_rejects_forged_support():
    from state_schema.provider_contracts import DeviceRegistration, MockConfiguration

    c = config()
    admitted = MockConfiguration.from_dict(c)
    registration = provider(c).discover()[0]
    assert DeviceRegistration.from_dict(
        registration.to_dict(), configuration=admitted
    ) == registration
    raw = registration.to_dict()
    raw["supported_capabilities"][0]["capability_version"] = True
    reject(lambda: DeviceRegistration.from_dict(raw, configuration=admitted))


@pytest.mark.tc019_02
def test_zero_position_observation_and_read_only_discovery():
    c = config()
    c["devices"][0]["supported_capabilities"] = [
        {"capability_id": "home.positionable", "capability_version": 1},
        {"capability_id": "home.battery_powered", "capability_version": 1},
    ]
    r = request()
    r.update(capability_id="home.positionable", action_id="set_position",
             arguments={"position_percent": 0})
    t = task(c, r=r)
    i = input_record(value=0)
    i.update(capability_id="home.positionable", member="position_percent")
    script(c, t, [delivery(1, i)])
    p = provider(c)
    assert ("home.battery_powered", 1) in p.discover()[0].supported_capabilities
    p.submit(t, binding=binding(), attempt_id="attempt-1")
    list(p.advance(1))
    value = p.snapshot()[0].to_dict()["reported_state"]["position_percent"]["value"]
    assert value == 0 and type(value) is int


@pytest.mark.parametrize("kind", ["property", "availability", "event"])
@pytest.mark.tc019_02
def test_input_unknown_field_and_malformed_event_are_safe(kind):
    c = policy_config("event_confirmed") if kind == "event" else config()
    t = task(c)
    i = input_record(kind)
    if kind == "event":
        i.update(member="changed", payload={"value": {"is_on": "private-value"},
                                           "ordering": {"epoch": 1, "sequence": 2}})
    else:
        i["private-field"] = "private-value"
    script(c, t, [delivery(0, i)])
    error = reject(lambda: provider(c))
    assert "private" not in str(error) and "private" not in repr(error.path)
