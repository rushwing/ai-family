"""TC-017-01: actual catalogue identity, schemas, units and exact lookup."""

from importlib.resources import files

import pytest
from capability_support import descriptor, reject
from initial_capabilities_support import CONTRACTS, RESOURCE, initial_required

pytestmark = initial_required


@pytest.mark.parametrize("identity,title,member,schema,read_only", CONTRACTS)
def test_exact_definition(initial_api, capability_api, identity, title, member, schema, read_only):
    catalogue = initial_api.load_initial_capabilities()
    raw = catalogue.get(identity, 1).to_dict()
    assert raw["schema_version"] == raw["capability_version"] == 1
    assert raw["title"] == title and raw["description"].strip()
    assert list(raw["properties"]) == [member]
    prop = raw["properties"][member]
    assert prop["value_schema"] == schema and prop["read_only"] is read_only
    assert prop["title"].strip() and prop["description"].strip()
    assert raw["events"] == {}
    assert capability_api.validate_capability(raw) == raw


def test_collection_and_duplicate_safe_resource(initial_api, capability_api):
    catalogue = initial_api.load_initial_capabilities()
    raw = catalogue.to_dict()
    assert list(raw) == ["schema_version", "capabilities"]
    assert [(d.capability_id, d.capability_version) for d in catalogue.capabilities] == [
        (c[0], 1) for c in CONTRACTS
    ]
    text = files("state_schema").joinpath(RESOURCE).read_text(encoding="utf-8")
    assert capability_api.load_capabilities_json(text).to_dict() == raw
    assert capability_api.validate_capabilities(raw) == raw
    # Closed project catalogue must not tighten the generic base validator.
    foreign = descriptor()
    assert capability_api.validate_capability(foreign) == foreign


@pytest.mark.parametrize("identity", [c[0] for c in CONTRACTS])
@pytest.mark.parametrize("revision", [0, 2, True, 1.0, "1"])
def test_no_version_fallback(initial_api, capability_api, identity, revision):
    reject(capability_api, lambda: initial_api.load_initial_capabilities().get(identity, revision))


def test_unknown_identity(initial_api, capability_api):
    reject(
        capability_api,
        lambda: initial_api.load_initial_capabilities().get("home.private", 1),
        private=("home.private",),
    )


@pytest.mark.parametrize(
    "identity,phrases",
    [
        ("home.switchable", ["true", "availability"]),
        ("home.positionable", ["percent", "0", "closed", "100", "open", "integer"]),
        ("home.temperature_sensor", ["celsius", "-273.15", "upper"]),
        ("home.humidity_sensor", ["relative humidity", "percent", "0", "100"]),
        ("home.power_meter", ["watts", "positive", "consumption", "negative", "generation"]),
        ("home.battery_powered", ["percent", "0", "100", "charging"]),
    ],
)
def test_normative_descriptions(initial_api, identity, phrases):
    raw = initial_api.load_initial_capabilities().get(identity, 1).to_dict()
    text = next(iter(raw["properties"].values()))["description"].lower()
    assert all(phrase in text for phrase in phrases)
