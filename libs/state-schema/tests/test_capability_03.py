"""TC-016-03: mandatory execution metadata without execution effects."""

import pytest
from capability_support import capability_required, changed, descriptor, reject

pytestmark = capability_required
ACTION = ("actions", "set_power")


@pytest.mark.parametrize("field", list(descriptor()["actions"]["set_power"]))
def test_action_required_fields(capability_api, field):
    data = descriptor()
    del data["actions"]["set_power"][field]
    reject(capability_api, lambda: capability_api.validate_capability(data), (*ACTION, field))


@pytest.mark.parametrize(
    "field,values",
    [
        ("risk", ["low", "medium", "high"]),
        ("idempotency", ["safe_repeat", "key_required", "non_idempotent"]),
        ("timeout_ms", [1, 86400000]),
    ],
)
def test_valid_metadata(capability_api, field, values):
    for value in values:
        assert capability_api.validate_capability(changed(descriptor(), (*ACTION, field), value))


@pytest.mark.parametrize(
    "field,value",
    [
        *(
            (field, value)
            for field in ("risk", "idempotency")
            for value in (None, True, 0, "unknown", "LOW", [])
        ),
        *(
            ("timeout_ms", value)
            for value in (None, False, True, 0, -1, 86400001, 1.0, "1000", float("inf"))
        ),
        ("completion_policy", None),
        ("completion_policy", {}),
        ("completion_policy", {"kind": "unknown"}),
        ("completion_policy", {"kind": "ack_only", "event": "changed"}),
        ("completion_policy", {"kind": "event_confirmed", "event": "changed", "targets": {}}),
        ("completion_policy", {"kind": "state_converged", "targets": {}, "event": "changed"}),
        ("input_schema", {"type": "integer"}),
    ],
)
def test_invalid_metadata(capability_api, field, value):
    reject(
        capability_api,
        lambda: capability_api.validate_capability(changed(descriptor(), (*ACTION, field), value)),
    )
