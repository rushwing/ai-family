"""TC-017-02: six actual scalar contracts, endpoints and type privacy."""

from copy import deepcopy

import pytest
from capability_support import reject
from initial_capabilities_support import CONTRACTS, initial_required

pytestmark = initial_required

VALID = [
    [True, False],
    [0, 50, 100],
    [-273.15, -10, 0, 21.5, 1e100],
    [0, 45.5, 100],
    [-125.5, 0, 230.25, 1e100],
    [0, 62.5, 100],
]
INVALID = [
    [None, 0, 1, "on"],
    [-1, 101, 50.0, True, "50", None],
    [-273.16, True, "21.5", None],
    [-0.1, 100.1, False, "45.5", None],
    [True, "230.25", None],
    [-0.1, 100.1, False, "62.5", None],
]
GOOD = [(c[0], c[2], value) for c, values in zip(CONTRACTS, VALID, strict=True) for value in values]
BAD = [
    (c[0], c[2], value) for c, values in zip(CONTRACTS, INVALID, strict=True) for value in values
]
BAD += [
    (c[0], c[2], value) for c in CONTRACTS for value in (float("nan"), float("inf"), -float("inf"))
]


@pytest.mark.parametrize("identity,member,value", GOOD)
def test_valid_property(initial_api, identity, member, value):
    result = initial_api.load_initial_capabilities().validate_payload(
        identity, 1, "property", member, value
    )
    assert result == value and type(result) is type(value)


@pytest.mark.parametrize("identity,member,value", BAD)
def test_invalid_property(initial_api, capability_api, identity, member, value):
    cat = initial_api.load_initial_capabilities()
    before = deepcopy(cat.to_dict())
    reject(capability_api, lambda: cat.validate_payload(identity, 1, "property", member, value))
    assert cat.to_dict() == before


@pytest.mark.parametrize("identity,title,member,schema,read_only", CONTRACTS)
def test_absence_is_not_a_value(
    initial_api, capability_api, identity, title, member, schema, read_only
):
    cat = initial_api.load_initial_capabilities()
    for value in ("unknown", "unavailable", {}, {"status": "unknown"}, "PRIVATE_MEASUREMENT"):
        reject(
            capability_api,
            lambda: cat.validate_payload(identity, 1, "property", member, value),
            private=("PRIVATE_MEASUREMENT",),
        )
    reject(
        capability_api,
        lambda: cat.validate_payload(identity, 1, "property", "private_value", 0),
        ("<unknown>",),
        private=("private_value",),
    )
