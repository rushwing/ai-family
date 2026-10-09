"""TC-014-02: strict shape failures and value-free deterministic diagnostics."""

from copy import deepcopy

import pytest
from binding_support import binding, binding_required, collection, error_at, mutated

pytestmark = binding_required
INVALID_TEXT = [None, True, 7, [], {}, "", " ", " leading", "trailing "]


@pytest.mark.parametrize("provider", ["ha", "mock"])
@pytest.mark.parametrize(
    "value",
    [
        "https://user:super-secret@ha.example:8123",
        "https://ha.example",
        "http%3A%2F%2Fha.example",
        "//ha.example:8123",
        "ha.example",
        "localhost:8123",
        "192.0.2.1",
        "[2001:db8::1]:8123",
        "user:super-secret@localhost",
        "user@localhost",
        "password=super-secret",
        "Bearer super-secret",
        "eyJhbGci.eyJzdWIi.signature",
        "ha/main",
        "ha\\main",
        "ha?token=super-secret",
        "ha#super-secret",
        "HA-main",
        "1-instance",
        "ha main",
        "h\u0430-main",
        "ha\nmain",
        "ha\x00main",
        "a" * 65,
    ],
)
def test_invalid_instance_alias_privacy(binding_api, inventory, provider, value):
    data = binding(provider, instance=value)
    document = collection(data)
    original = deepcopy(document)
    private = (value, "super-secret", "ha.example")
    for call in (
        lambda: binding_api.ProviderBinding.from_dict(data),
        lambda: binding_api.validate_binding(data),
    ):
        error_at(binding_api, call, ("provider_instance_id",), private=private)
    for call in (
        lambda: binding_api.BindingCollection.from_dict(document, inventory=inventory),
        lambda: binding_api.validate_bindings(document, inventory=inventory),
    ):
        error_at(binding_api, call, ("bindings", 0, "provider_instance_id"), private=private)
    assert document == original


@pytest.mark.parametrize("provider", ["ha", "mock"])
@pytest.mark.parametrize(
    "field", ["home_id", "device_id", "provider", "provider_instance_id", "mapping"]
)
def test_missing_fields(binding_api, provider, field):
    data = binding(provider)
    del data[field]
    error_at(binding_api, lambda: binding_api.validate_binding(data), (field,))


@pytest.mark.parametrize("field", ["home_id", "device_id", "provider_instance_id"])
@pytest.mark.parametrize("value", INVALID_TEXT)
def test_required_text(binding_api, field, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(mutated(binding(), (field,), value)),
        (field,),
    )


@pytest.mark.parametrize("field", ["home_id", "device_id"])
@pytest.mark.parametrize("value", ["Bad_ID", "bad.id", "a" * 65, "1-start"])
def test_canonical_id_vocabulary(binding_api, field, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(mutated(binding(), (field,), value)),
        (field,),
    )


@pytest.mark.parametrize("value", [*INVALID_TEXT, "HA", "homeassistant", "unknown-private-value"])
def test_provider_discriminator(binding_api, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(mutated(binding(), ("provider",), value)),
        ("provider",),
        private=("unknown-private-value",),
    )


@pytest.mark.parametrize("provider", ["ha", "mock"])
@pytest.mark.parametrize("value", [None, True, 0, "", []])
def test_mapping_object(binding_api, provider, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(mutated(binding(provider), ("mapping",), value)),
        ("mapping",),
    )


@pytest.mark.parametrize("provider,field", [("ha", "entity_ids"), ("mock", "device_key")])
def test_missing_mapping_key(binding_api, provider, field):
    data = binding(provider)
    del data["mapping"][field]
    error_at(binding_api, lambda: binding_api.validate_binding(data), ("mapping", field))


@pytest.mark.parametrize("value", [None, True, 0, "", {}, (), []])
def test_entity_list(binding_api, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(mutated(binding(), ("mapping", "entity_ids"), value)),
        ("mapping", "entity_ids"),
    )


@pytest.mark.parametrize("value", INVALID_TEXT)
def test_entity_members(binding_api, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(
            mutated(binding(), ("mapping", "entity_ids"), ["light.fictional", value])
        ),
        ("mapping", "entity_ids", 1),
    )


def test_duplicate_entity_privacy(binding_api):
    value = "fictional-sensitive-entity"
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(
            mutated(binding(), ("mapping", "entity_ids"), [value, value])
        ),
        ("mapping", "entity_ids", 1),
        private=(value,),
    )


@pytest.mark.parametrize("provider,field", [("ha", "device_registry_id"), ("mock", "device_key")])
@pytest.mark.parametrize("value", [True, 0, [], {}, "", " ", " private-marker "])
def test_mapping_text(binding_api, provider, field, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(mutated(binding(provider), ("mapping", field), value)),
        ("mapping", field),
        private=("private-marker",),
    )


@pytest.mark.parametrize("provider", ["ha", "mock"])
@pytest.mark.parametrize("field", ["token", "url", "service", "action", "metadata"])
def test_unknown_mapping_metadata(binding_api, provider, field):
    data = binding(provider)
    data["mapping"][field] = {"private-marker": "fictional-secret"}
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(data),
        ("mapping", field),
        private=("private-marker", "fictional-secret"),
    )


@pytest.mark.parametrize(
    "provider,field,value",
    [
        ("ha", "device_key", "fictional"),
        ("mock", "entity_ids", ["light.fictional"]),
        ("mock", "device_registry_id", None),
    ],
)
def test_mixed_mapping(binding_api, provider, field, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(mutated(binding(provider), ("mapping", field), value)),
        ("mapping", field),
    )


@pytest.mark.parametrize("value", [True, False, 0, 2, 1.0, "1", None, [], {}])
def test_version(binding_api, inventory, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(
            {"schema_version": value, "bindings": []}, inventory=inventory
        ),
        ("schema_version",),
    )


@pytest.mark.parametrize("value", [None, True, 1, "", {}, ()])
def test_bindings_list(binding_api, inventory, value):
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(
            {"schema_version": 1, "bindings": value}, inventory=inventory
        ),
        ("bindings",),
    )


@pytest.mark.parametrize("value", [None, True, 1, "", [], {1: "private-marker"}])
def test_root_objects(binding_api, inventory, value):
    error_at(
        binding_api, lambda: binding_api.validate_binding(value), (), private=("private-marker",)
    )
    error_at(binding_api, lambda: binding_api.validate_bindings(value, inventory=inventory), ())


@pytest.mark.parametrize("field", ["schema_version", "bindings"])
def test_missing_envelope(binding_api, inventory, field):
    data = collection()
    del data[field]
    error_at(
        binding_api, lambda: binding_api.validate_bindings(data, inventory=inventory), (field,)
    )


def test_unknown_envelope_and_binding(binding_api, inventory):
    data = {**collection(), "metadata": "private-marker"}
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(data, inventory=inventory),
        ("metadata",),
        private=("private-marker",),
    )
    error_at(
        binding_api,
        lambda: binding_api.validate_binding({**binding(), "token": "private-marker"}),
        ("token",),
        private=("private-marker",),
    )
    invalid = deepcopy(collection(binding()))
    invalid["bindings"][0]["mapping"]["entity_ids"] = [" private-marker "]
    error_at(
        binding_api,
        lambda: binding_api.validate_bindings(invalid, inventory=inventory),
        ("bindings", 0, "mapping", "entity_ids", 0),
        private=("private-marker",),
    )


def test_null_mock_key_and_registry_only_ha(binding_api):
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(
            mutated(binding("mock"), ("mapping", "device_key"), None)
        ),
        ("mapping", "device_key"),
    )
    data = binding()
    data["mapping"] = {"device_registry_id": "fictional-registry"}
    error_at(binding_api, lambda: binding_api.validate_binding(data), ("mapping", "entity_ids"))


@pytest.mark.parametrize("provider", ["ha", "mock"])
def test_nonstring_mapping_keys(binding_api, provider):
    data = binding(provider)
    data["mapping"][1] = "private-marker"
    error_at(
        binding_api,
        lambda: binding_api.validate_binding(data),
        ("mapping",),
        private=("private-marker",),
    )
