"""TC-017-04: snapshots, fixed resource revalidation and private failures."""

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest
from capability_support import reject
from initial_capabilities_support import RESOURCE, initial_required, inject_resource

pytestmark = initial_required


@pytest.mark.parametrize("change", ["identity", "schema", "action", "order", "property", "clear"])
def test_detached_snapshots_and_fresh_records(initial_api, change):
    first = initial_api.load_initial_capabilities()
    baseline = deepcopy(first.to_dict())
    exported = first.to_dict()
    records = exported["capabilities"]
    if change == "identity":
        records[0]["capability_id"] = "private.changed"
    elif change == "schema":
        records[1]["properties"]["position_percent"]["value_schema"]["maximum"] = 1000
    elif change == "action":
        records[0]["actions"]["set_on"]["completion_policy"]["targets"].clear()
    elif change == "order":
        records.reverse()
    elif change == "property":
        records[0]["properties"]["is_on"]["read_only"] = True
    else:
        records.clear()
    second = initial_api.load_initial_capabilities()
    assert first.to_dict() == second.to_dict() == baseline
    assert first is not second and first.capabilities[0] is not second.capabilities[0]
    with pytest.raises(FrozenInstanceError):
        first.capabilities[0].capability_version = 2


@pytest.mark.parametrize(
    "fault",
    [
        "syntax",
        "duplicate",
        "extra_key",
        "invalid_schema",
        "empty",
        "missing",
        "extra",
        "revision",
        "order",
    ],
)
def test_malformed_catalogue(initial_api, capability_api, monkeypatch, fault):
    raw = initial_api.load_initial_capabilities().to_dict()
    if fault == "syntax":
        text = '{"PRIVATE_CONTENT":'
    elif fault == "duplicate":
        text = json.dumps(raw).replace(
            '"is_on": {', '"PRIVATE_KEY":0,"PRIVATE_KEY":1,"is_on": {', 1
        )
    else:
        if fault == "extra_key":
            raw["capabilities"][0]["PRIVATE_KEY"] = "PRIVATE_CONTENT"
        elif fault == "invalid_schema":
            raw["capabilities"][0]["properties"]["is_on"]["value_schema"]["unit"] = (
                "PRIVATE_CONTENT"
            )
        elif fault == "empty":
            raw["capabilities"] = []
        elif fault == "missing":
            raw["capabilities"].pop()
        elif fault == "extra":
            extra = deepcopy(raw["capabilities"][0])
            extra["capability_id"] = "private.extra"
            raw["capabilities"].append(extra)
        elif fault == "revision":
            raw["capabilities"][0]["capability_version"] = 2
        else:
            raw["capabilities"].reverse()
        text = json.dumps(raw)
    calls = inject_resource(monkeypatch, initial_api, text=text)
    reject(
        capability_api,
        initial_api.load_initial_capabilities,
        private=("PRIVATE_KEY", "PRIVATE_CONTENT", "private.extra"),
    )
    assert calls == [("files", "state_schema"), ("joinpath", RESOURCE), ("read_text", "utf-8")] * 2


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("PRIVATE_PATH"),
        PermissionError("PRIVATE_PATH"),
        OSError("PRIVATE_PATH"),
        UnicodeDecodeError("utf-8", b"PRIVATE_BYTES", 0, 1, "PRIVATE_REASON"),
    ],
)
def test_resource_read_errors(initial_api, capability_api, monkeypatch, error):
    inject_resource(monkeypatch, initial_api, error=error)
    reject(
        capability_api,
        initial_api.load_initial_capabilities,
        ("capabilities",),
        private=("PRIVATE_PATH", "PRIVATE_BYTES", "PRIVATE_REASON"),
    )


def test_each_call_reloads_and_revalidates(initial_api, capability_api, monkeypatch):
    text = json.dumps(initial_api.load_initial_capabilities().to_dict())
    calls = inject_resource(monkeypatch, initial_api, text=text)
    first = initial_api.load_initial_capabilities()
    second = initial_api.load_initial_capabilities()
    assert first is not second and first.to_dict() == second.to_dict()
    assert calls == [("files", "state_schema"), ("joinpath", RESOURCE), ("read_text", "utf-8")] * 2
    inject_resource(monkeypatch, initial_api, text="{}")
    reject(capability_api, initial_api.load_initial_capabilities)
