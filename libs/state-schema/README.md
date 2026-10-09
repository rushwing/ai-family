# Canonical home inventory, bindings, State, Capability and Action contracts

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
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime -q
ruff check libs/state-schema/src libs/state-schema/tests
mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
```

Acceptance mode rejects absent runtime or any skipped test. CI runs these checks
on Python 3.12/3.13/3.14 and uploads JUnit results. Package wheel installation and CLI/API
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
TCs: [REQ-015](../../harness/tasks/archive/done/features/REQ-015.md). PR #31
merged as `58f411e`; human-001 accepted AC1–AC7 and TC-015-01–06
under the explicit merge disposition. REQ-015 is archived done; no independent
evaluator signature is inferred. See [closeout evidence](../../harness/tasks/evidence/REQ-015-review-acceptance.md).

Canonical ID validation in all three contract modules uses the shared
`home_inventory.CANONICAL_ID_PATTERN`. State timestamps enforce hour 0–23,
minute/second 0–59 before calendar parsing, so interpreter parser normalization
cannot broaden the accepted contract. CI runs State validation, lint/type and
installed-wheel smoke on Python 3.12, 3.13 and 3.14; these Linux checks do not
claim Termux runtime validation.

## Versioned Capability Base — REQ-016

`state_schema.capability` provides immutable typed descriptors/catalogues and
pure payload validators. The [fictional catalogue](../../docs/product/home-intelligence/examples/capability-base.example.json)
contains `demo.power` revision 1; this is a base-contract fixture, not HI-S012's
six concrete capability definitions or a Device/provider attachment.

```python
from state_schema.capability import load_capabilities_json, validate_payload

catalogue = load_capabilities_json(json_text)  # text supplied by the caller; no file I/O
capability = catalogue.get("demo.power", 1)  # exact revision, never latest fallback
validated = capability.validate_payload("action_input", "set_power", {"power": False})
accepted = catalogue.validate_payload(
    "demo.power", 1, "action_output", "set_power", {"accepted": True}
)
assert validate_payload({"type": "integer", "minimum": 0}, 0) == 0
```

`CapabilityDescriptor.from_dict` / `CapabilityCatalogue.from_dict` validate
external objects; `validate_capability` / `validate_capabilities` return detached
JSON snapshots. `load_capability_json` / `load_capabilities_json` accept strings
and reject duplicate keys at every object level, malformed text and nonfinite
constants. Already-parsed dictionaries cannot recover keys discarded by an
upstream decoder. `Schema`, `Property`, `Action`, `Event`, `CompletionPolicy`
and `TargetSource` also expose validating factories and detached snapshots.
Direct constructors are internal typed records; public payload/lookup methods
revalidate records. Nested collections are tuples; no mutable caller data is
retained. Interaction kinds are `property`, `action_input`, `action_output`,
`event`; unknown names/kinds and unsupported exact revisions fail closed.

Capability IDs have 2–4 dot-separated segments of 1–32 characters each;
the maximum total length is 131 characters (4 × 32 + 3 separators).

The bounded schema profile supports seven JSON types and the documented
scalar enum/bound, object required/closed-property and array-item/length
constraints. It rejects unlisted keywords, references, defaults, composition,
nonfinite numbers and coercion. Schema depth counts root/child schema nodes;
payload depth independently counts actual root/member/element JSON values,
with a maximum of 16 in each tree. Bool never equals a numeric enum/target.
State-converged input/property schemas require recursive structural equality:
object key order is ignored, list order retained, missing constraints never
receive defaults, and integer/float numbers compare numerically.

Every action requires risk (`low`/`medium`/`high`), timeout 1–86400000 ms,
idempotency (`safe_repeat`/`key_required`/`non_idempotent`) and one completion
policy: `ack_only`, `event_confirmed` with a declared event, or `state_converged`
with writable-property targets from required matching input fields/valid
constants. These declarations grant no authorization and run no deadlines,
correlation, deduplication or completion engine. A validated `accepted` output
cannot set reported State, availability or ordering; physical convergence
still requires REQ-015's eligible post-baseline current-generation reports.

`CapabilityError.path` / `.message` provide deterministic value-free errors.
Unknown keys and invalid names are redacted; duplicate text keys use
`("<unknown>",)`. This duplicate-key path is fixed even for nested objects:
the JSON object-pairs hook does not provide the containing path, so it cannot
locate the duplicate within a large document. Numeric and length bound errors
append the violated schema keyword to the payload node path: root string
overflow is `("maxLength",)`, and nested array underflow can be
`("values", "minItems")`. These suffixes name constraints, not payload fields.
Root type and enum failures retain `()` because the value node is the root.
For descriptor payload selection, a canonical but undeclared interaction name
uses `("<unknown>",)`; malformed names use `("<property>",)`. Neither error
echoes the supplied name, so undeclared interactions have no member location.
There is no provider client, dispatch, store, clock or runtime
dependency. Required acceptance adds `--require-capability-runtime`; missing
runtime or any skip fails. PR #32 is merged; human-001 accepted AC1–AC7 and TC-016-01–06 under
the final merge disposition. REQ-016 is archived done; no independent evaluator
signature is inferred. See [closeout evidence](../../harness/tasks/evidence/REQ-016-review-acceptance.md), [REQ-016](../../harness/tasks/archive/done/features/REQ-016.md)
and [runtime self-check evidence](../../harness/tasks/evidence/REQ-016-runtime-implementation.md).

## Six Initial Capabilities — REQ-017

```python
from state_schema.initial_capabilities import load_initial_capabilities

catalogue = load_initial_capabilities()
catalogue.validate_payload("home.switchable", 1, "action_input", "set_on", {"is_on": False})
catalogue.validate_payload("home.power_meter", 1, "property", "power_w", -125.5)
```

The no-argument accessor reads the fixed UTF-8 package resource
[initial_capabilities.v1.json](src/state_schema/initial_capabilities.v1.json)
on each call, validates duplicate keys and the complete REQ-016 contract, then
requires exactly the six ordered revision-1 identities. It returns fresh immutable
records with detached snapshots. There is no import-time catalogue read or cache.
Missing/unreadable resource errors of type `OSError` or `UnicodeError` are
wrapped in value-free `CapabilityError` diagnostics. Other resource-loader
exception classes have no promised fixed-message wrapper.

Runtime checks enforce structural validity and the exact ordered identity/revision
pairs. Equality with this specification's schemas, metadata, titles and unit wording
is checked by independently transcribed TCs, version-controlled review and release
checks; the accessor performs no frozen-digest or full expected-content comparison.
Keep `_IDENTITIES`, the packaged resource and independent test expectations
synchronized when reviewing catalogue revisions. Clients should treat error paths
as diagnostic locations, not use their differing shapes to dispatch recovery logic.

| Identity | Property | Unit and range | Action |
|---|---|---|---|
| `home.switchable` | `is_on` | Boolean on/off, separate from availability | `set_on` |
| `home.positionable` | `position_percent` | Integer opening percent, 0 closed / 100 open | `set_position` |
| `home.temperature_sensor` | `temperature_c` | Celsius, minimum -273.15; finite numbers | none |
| `home.humidity_sensor` | `relative_humidity_percent` | Relative humidity percent, 0–100 | none |
| `home.power_meter` | `power_w` | Signed watts; positive import, negative export | none |
| `home.battery_powered` | `battery_percent` | Remaining charge percent, 0–100 | none |

Clients must deliberately support the exact `(identity, revision, property)`
meaning to interpret units and direction. Descriptions do not grant compatibility;
there is no `unit` schema keyword or automatic conversion. All measurements are
read-only; all event maps are empty. Unknown/offline stays in REQ-015 State metadata,
never a fabricated false/zero reading. Exact-version selection never falls back.

Both actions declare `medium` risk, `safe_repeat` intent and `state_converged`
completion; dispatch deadlines are 30000 ms for `set_on` and 120000 ms for
`set_position`. Inputs require their single canonical property, outputs are null.
These declarations execute nothing and grant no authorization or retry guarantee.
ACK/null output cannot establish observed convergence. Future integrations must
validate canonical reports before applying State updates: generic State helpers
do not enforce Capability types, and a float position is rejected by this
Capability contract even though generic State supports numeric scalar comparison.
No provider adapter, task engine, Device attachment or store integration is added.

[REQ-017](../../harness/tasks/archive/done/features/REQ-017.md) owns the specification and
lifecycle. PR #34 is merged; human-001 accepted AC1–AC7 and TC-017-01–06
under the explicit merge/archive disposition. REQ-017 is archived done; no
independent evaluator signature is inferred. See
[closeout evidence](../../harness/tasks/evidence/REQ-017-review-acceptance.md).

## Action Request, Result and Task (REQ-018)

`state_schema.action_contracts` adds version-1 pure action contracts. It neither
executes actions nor authenticates a requester. Device capability support,
authorization/confirmation, durable tasks/idempotency/audit, deadlines and provider
integration remain separate prerequisites before writes. TC/feature acceptance
is pending external review; see [REQ-018](../../harness/tasks/features/REQ-018.md).

Use `validate_request(data, *, requester, inventory, catalogue)` or
`create_task(data, *, requester, task_id, inventory, catalogue)` at the trusted
boundary. All context objects are explicit JSON snapshots; use Inventory and
CapabilityCatalogue `.to_dict()` for typed records. Wire Request fields are exactly
schema_version/home_id/device_id/capability_id/capability_version/action_id/arguments/
idempotency_key/trace_id. Requester is a separate trusted input with
subject_id/family_member_id/home_id/role (`admin`, `adult`, `kid`). A role or selected
catalogue action proves no membership, Device support, permission or confirmation.
Do not use `from_dict()` to authenticate a client or establish trusted completion.

`ActionRequest`, `RequesterContext`, `ActionResult` and `Task` factories validate
shape only, return frozen records, and expose detached `.to_dict()` snapshots.
Nested JSON is stored as immutable text internally; arguments/output/evidence
properties also return detached snapshots. Contextual validators revalidate exact
Inventory references, catalogue revision, action input/output and completion evidence.
Direct constructors remain internal-only. External unknown fields, non-JSON/cyclic/
nonfinite payloads and depth above 16 reject; unusually large integers that the
interpreter cannot JSON-encode also reject with a fixed value-free error.

Idempotency/task/trace identifiers are exact case-sensitive ASCII tokens of 1–128
characters from letters/digits/`.`/`_`/`:`/`-`, without trim or normalization.
Requester `subject_id` and `family_member_id` are nonblank strings of at most 256
characters, retained exactly; spaces and Unicode are allowed. These externally
established identity strings have a separate grammar from contract correlation
tokens, so identity providers need no token-alphabet conversion. Requester `home_id`
still follows the canonical Inventory grammar.
`compare_idempotency(task, request, *, requester, inventory, catalogue)` returns
`distinct`, `replay` or `conflict` in the Home/member/subject/key scope. Replay
retains the original Task and trace. Argument comparison is recursively type-exact:
230 and 230.0 conflict even for a number schema; object-key order is irrelevant.
This differs deliberately from Capability enum and State numeric equality. There
is no key reservation, concurrency/restart protection or dispatch in this package.

`create_task` starts accepted with caller-provided IDs and null result/dispatch_context.
`transition_task(task, result, *, inventory, catalogue, dispatch_context=None)` requires
an explicit `{current_epoch, baseline}` when accepted becomes running, then freezes
that context. Even immediate ACK/success evidence must pass through running. The
baseline may be null for uncertain execution; success needs an eligible current-epoch
baseline. Task snapshots retain the descriptor's exact completion policy. Result
fields and every allowed edge are fixed in REQ-018's seam and transition table.
`validate_result(result, *, task, inventory, catalogue)` checks context/evidence;
`transition_task` additionally checks transition legality. `validate_task` validates
the stored Result against the Task state and descriptor. Loading a trusted snapshot
is structural validation, not proof of the caller's claimed provenance/history.

Result `output` is `{present, value}`: absent requires null, while present null must
still pass the declared output schema. Error is null except failed/timed_out, which
require a stable `{code}`. This revision does not represent cancellation reasons:
cancelled requires null error. Evidence is separate and repeats exact task/trace/action
identity; kinds are ack/event/state. All non-success outcomes say physical_outcome
unverified. `ack_only` can terminate as acknowledged, never succeeded. ACK/output
alone cannot confirm an event or observed state. Terminal tasks do not regress;
exact same-state Result replay is a no-op, conflicting replay rejects. Recording a
new ACK on an already-running task would be a conflicting Result replay: record it
on the explicit accepted → running step, or retain it in the later service's separate
transport telemetry. This pure slice is not an incremental progress-event store.

Event completion validates the declared payload and trusted correlated ordering
strictly after the frozen baseline in the current epoch. State completion first
validates relevant known target observations through the actual Capability property
schemas, then derives intent from Request/descriptor and calls actual State convergence.
Submitted State desired_state never chooses targets or rebases dispatch. This prevents
float positions from bypassing the initial integer schema through generic State numeric
equality. Unknown/offline/stale/missing/wrong-epoch/mismatched observations cannot
confirm; false/zero retain their meaning. Event confirmation and State agreement do
not establish command causation. Cancellation/timeout do not promise physical rollback
or safe retry; later durable reconciliation must handle uncertain outcomes.

`ActionError.path`/`.message` are deterministic value-free diagnostics, not a recovery
protocol. Upstream failures are wrapped with fixed reasons and suppressed context;
no raw provider exception or private argument is accepted as an error description.
Helpers perform no file/network/clock/environment lookup, allocation or State mutation.

Required acceptance adds `--require-action-runtime` to all five previous required-runtime
options. CI runs the package on Python 3.12/3.13/3.14 plus lint/type and isolated
installed-wheel Request/Task/Result smoke. Executed tests are author evidence, not
independent T07/T10/T13 approval.
