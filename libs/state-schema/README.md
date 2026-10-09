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
separately from inventory. [PR #29](https://github.com/rushwing/ai-family/pull/29) is merged; human-001’s
final acceptance and post-merge verification are recorded in
[closeout evidence](../../harness/tasks/evidence/REQ-014-review-acceptance.md). No provider runtime or dispatch path is introduced.

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
opaque `provider_instance_id`, and a discriminated `mapping`. The instance must
be a nonsensitive local alias matching `^[a-z][a-z0-9_-]{0,63}$` (1–64 ASCII
characters). URL, host-port, user-info and credential-assignment syntax is rejected
with value-free diagnostics. Store endpoints and credentials in separate connection
configuration; arbitrary ID-shaped secrets cannot be detected by syntax validation.
HA requires a
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

## Canonical State (REQ-015)

`state_schema.canonical_state` supplies offline version-1 State contracts and
pure ordering/convergence helpers. State lives separately from inventory and
ProviderBinding. `DeviceState.from_dict` / `validate_state` validate individual
shape; `StateCollection.from_dict` / `validate_states(data, inventory=...)` also
validate inventory references and one record per Device. Direct dataclass
constructors are internal typed records; use factories for external input.
Frozen nested records and tuple property maps expose detached `to_dict()` JSON.
There are no omitted-field defaults. Scalar bool/int/float/string types and
observation timestamp spellings are preserved.

```python
from state_schema.canonical_state import validate_state, apply_state_update, evaluate_convergence

snapshot = validate_state(my_state_document)
updated = apply_state_update(
    snapshot, current_epoch=1,
    reported_state={"power": {
        "status": "known", "value": False,
        "observed_at": "2026-01-01T12:00:00Z",
        "ordering": {"epoch": 1, "sequence": 2},
    }},
)
result = evaluate_convergence(updated, current_epoch=1)
```

`desired_state` is nullable intent with a positive revision, nonempty `values`
and nullable `report_baseline`. Reports are per-property tagged observations;
known requires a scalar and UTC observation time/order, unknown requires null
value and either paired null metadata or actual observation metadata.
Availability is independently tagged online/offline/unknown. Current-generation
online availability may predate the intent baseline; the strict post-baseline
requirement applies to each desired property report. Offline preserves
last known false/zero values without making them currently confirmed evidence.
Unknown, absent property and literal known string `"unknown"` remain distinct.

The owner explicitly supplies `current_epoch` to both helpers. Higher epochs
establish generations; lower-than-accepted context is rejected. Updates must
belong to the established epoch, including after sequence resets. Greater
member ordering replaces; stale updates are ignored; identical typed replay is
idempotent and conflicting equal-order replay fails. Each property and
availability compares its own accepted pair. Timestamps never determine order.
Equal replay preserves exact numeric types; convergence compares numbers by
numeric value while keeping booleans distinct. Batch errors never mutate input.

Update arguments omitted or None mean no update. A null-metadata unknown
snapshot cannot be applied as an event; explicit unknown events need order/time.
Intent changes use independent revision ordering. Null intent cancellation
through the update helper is not supported because it carries no new revision.
The caller supplies counters/epochs; the module provides no store, allocation,
clock-based TTL or restart coordination. The owner must retain the established
epoch even before refreshed observations record it; stateless validation can
only detect context rollback against epochs present in the supplied snapshot.
Shape-only helpers prove no inventory
integrity or authenticity of submitted observations.

Convergence yields `not_requested`, `unknown`, `pending` or `confirmed`.
Confirmation requires current-epoch online availability and every desired
property known, matching and strictly later than the intent baseline in that
epoch. Missing/null/cross-epoch baselines or ineligible reports yield unknown.
A generation change requires explicit intent rebasing with a higher revision.
Agreement does not prove that a command caused the change. ACK/task success is
outside State and cannot create observed values/time/order or online status.
There is no dispatch or provider runtime; unknown completion fields reject.

`StateError.path` / `.message` locate failures without supplied values. Unknown
structural keys and malformed property names are redacted as `<unknown>` and
`<property>`; valid canonical property names remain useful in paths. Invalid
inventory errors retain schema fields/indices with an inventory prefix and
generic reason; arbitrary submitted inventory keys become `<unknown>`. The
legacy inventory validator keeps its own original diagnostic convention.
The public [fictional timeline](../../docs/product/home-intelligence/examples/canonical-state-timeline.example.json)
shows intent → ACK only → actual mismatch → matching false/zero observations.
It is an example bundle, not the State collection envelope or a live integration.

Required runtime acceptance adds `--require-state-runtime` to the shared pytest
command. Missing module or any skip fails acceptance. Specification and required
TCs: [REQ-015](../../harness/tasks/features/REQ-015.md). Independent combined
TC/feature review remains pending; passing self-checks do not mark delivery done.

Canonical ID validation in all three contract modules uses the shared
`home_inventory.CANONICAL_ID_PATTERN`. State timestamps enforce hour 0–23,
minute/second 0–59 before calendar parsing, so interpreter parser normalization
cannot broaden the accepted contract. CI runs State validation, lint/type and
installed-wheel smoke on Python 3.12, 3.13 and 3.14; these Linux checks do not
claim Termux runtime validation.
