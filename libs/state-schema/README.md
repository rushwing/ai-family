# Canonical home inventory and provider bindings

REQ-013 implements provider-neutral Home, Floor, Area, Device, Label and AreaGroup
contracts, a UTF-8 JSON loader and pure target resolution. The public apartment
fixture is fictional. This package has no provider credentials, network client,
action dispatcher, persistence or automatic inventory discovery.

Install from the repository root with Python 3.12+:

```bash
python -m pip install -e 'libs/state-schema[test]'
python -m state_schema.home_inventory docs/product/home-intelligence/examples/three-bedroom-apartment.example.json
```

The command validates the explicit path and prints normalized JSON. It never
modifies the file. Missing/unreadable files, invalid UTF-8/JSON, duplicate JSON
fields, nonstandard numeric constants and contract violations exit 2 with the
file and cause on stderr. Schema errors also include a JSON field path.

## Python API

```python
from state_schema.home_inventory import Inventory, load_inventory, resolve_targets

inventory = load_inventory("my.home-inventory.local.json")
domain = Inventory.from_dict(inventory)
assert domain.schema_version == 1

result = resolve_targets(
    inventory,
    home_id=domain.home.id,
    selector={"area_group_ids": ["resting"], "label_ids": ["children"]},
)
```

`validate_inventory(data)` normalizes external dictionaries and rejects unknown
fields, wrong scalar/list types, duplicate IDs/members, vocabulary errors,
dangling references and cross-home containment. IDs remain independent of names,
array positions, floor levels and provider identities. Omitted optional labels
and aliases become empty lists; nullable containment fields remain explicit.

`Inventory.from_dict` and each record's `from_dict` factory validate external
values. Inventory validation additionally verifies global identity/containment.
Direct dataclass constructors are for statically typed internal records and do
not validate external input. The records are frozen and nested collections are
tuples. `to_dict()` produces a detached JSON-compatible snapshot, so editing a
snapshot cannot change an existing domain object's identity. Revalidate edited
snapshots while retaining IDs for renamed/moved objects.

Groups union matching area types; label filters require every requested label on
the area. Returned area/device IDs are sorted and unique. Unassigned devices do
not match; areas without a floor remain selectable. Valid empty results stay
empty. Unknown or ambiguous selectors fail explicitly, without a whole-home
fallback. The resolver revalidates the supplied inventory and makes no writes.
A selected label or group conveys no action permission.

`InventoryError.path` is a tuple of field names/list indices. The exception text
uses `$` paths such as `$.areas[0].floor_id`. The JSON-facing functions return
fresh dictionaries; the frozen models provide typed domain access.

## Validation and design decision

Validation uses Python's standard library, frozen dataclasses and explicit
shape/reference checks. The schema is small and fixed; this avoids scalar
coercion and keeps the loader available without external runtime dependencies.
Fields are inspected in declared order; global ID checks precede reference
checks. The supplied independent combined review accepted this implementation choice.

Run the required checks from the repository root:

```bash
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime --require-binding-runtime -q
ruff check libs/state-schema/src libs/state-schema/tests
mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
```

Acceptance mode rejects absent runtime or any skipped test. CI runs these checks
on Python 3.12 and uploads JUnit results. Package wheel installation and CLI/API
smoke verification are also recorded in Harness evidence. The completed independent combined review and post-polish acceptance are recorded
in [Harness evidence](../../harness/tasks/evidence/REQ-013-review-acceptance.md);
completion follows the Harness merge gate.

See [REQ-013](../../harness/tasks/archive/done/features/REQ-013.md),
[TC execution instructions](tests/README.md) and the
[editable apartment workflow](../../docs/product/home-intelligence/examples/README.md).

## ProviderBinding (REQ-014)

`state_schema.provider_binding` implements offline, version-1 mapping contracts
separately from inventory. Independent combined TC/code review is pending in
[PR #29](https://github.com/rushwing/ai-family/pull/29); self-check results do not
mark REQ-014 complete. No provider runtime or dispatch path is introduced.

```python
import json
from pathlib import Path
from state_schema.home_inventory import load_inventory
from state_schema.provider_binding import BindingCollection, validate_binding, validate_bindings

inventory = load_inventory("docs/product/home-intelligence/examples/three-bedroom-apartment.example.json")
fixture = json.loads(Path("docs/product/home-intelligence/examples/provider-binding-replacement.example.json").read_text())
before = BindingCollection.from_dict(fixture["before"], inventory=inventory)
after = validate_bindings(fixture["after"], inventory=inventory)
assert before.bindings[0].device_id == after["bindings"][0]["device_id"]
shape_only = validate_binding(fixture["before"]["bindings"][0])
```

`ProviderBinding.from_dict(data)` / `validate_binding(data)` validate individual
shape only; they do not prove that a Home/Device exists. `BindingCollection.from_dict`
/ `validate_bindings` additionally require a JSON inventory snapshot, revalidate
its canonical references, and reject duplicate Device bindings and same-instance
resource collisions. Pass `Inventory.to_dict()` if starting with a typed inventory.
Direct dataclass constructors are internal typed records and do not validate
external input; always use the factories at external boundaries.

Each binding has `home_id`, `device_id`, exact provider kind `ha` or `mock`, an
opaque `provider_instance_id`, and a discriminated `mapping`. HA requires a
nonempty distinct `entity_ids` list and optionally `device_registry_id` (omitted
normalizes to null). Mock requires `device_key`. All identifiers in mappings are
nonempty trimmed opaque strings: no live resource existence or HA syntax check
is performed. One Device has at most one binding per collection; an empty or
partial collection is valid. Resource uniqueness is scoped to provider kind and
instance; HA registry IDs may be shared if entity sets are disjoint.

Frozen models and tuple entity lists isolate typed records; `to_dict()` returns
fresh JSON snapshots. Only a successfully validated candidate should replace an
application's accepted snapshot. This package exposes no replacement/update
operation or persistence. The example compares two separate fictional collections;
canonical identity and inventory are unchanged, with no live provider switch.

`BindingError.path` and `.message` describe the offending field/index and reason
without echoing supplied values. Invalid inventory uses an `inventory` path prefix
with a generic reason to avoid forwarding inventory diagnostics containing private
identifiers. Do not log raw binding documents. Unknown fields, credentials,
action templates and executable metadata fields are rejected. A valid mapping
confers no permission and proves neither availability nor capability support.

Keep real mappings in Git-ignored `*.provider-bindings.local.json` files; public
fixtures are fictional. No new inventory schema, loader, adapter, API route or
runtime dependency is needed. Standard-library validation follows the existing
package design and remains subject to independent implementation review.
