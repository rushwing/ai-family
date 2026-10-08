# Canonical home inventory

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
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime -q
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
