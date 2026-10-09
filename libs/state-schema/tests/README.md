# REQ-013 acceptance tests

TC-013-01–07 implement the reviewed acceptance text against the delivered
inventory package. Tests call the public API directly and never substitute a
fake validator, loader or resolver. Frozen-record and strict JSON decoding
regressions supplement the original TC code. The guard checks are
infrastructure checks; all remaining cases execute the runtime.

The independent combined TC-code/feature review supplied by human-001 passed. Successful test execution
is implementation evidence, not an independent approval.

Run from the repository root with Python 3.12+ and pytest:

```bash
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime -q
```

The isolated pytest configuration adds `libs/state-schema/src` to the import
path and does not collect unrelated service integration tests. The package
supplies metadata and frozen dataclass models. Validation uses the standard
library with no runtime dependencies; see the [package instructions](../README.md).

## Public test seam

The `state_schema.home_inventory` module exposes these JSON-facing functions.
`Inventory.from_dict` provides the validated frozen domain model. Public API
changes require review and must preserve the acceptance assertions.

| Entry point | Tested interface |
|---|---|
| `validate_inventory(data)` | Accept a version-1 JSON object; return a normalized JSON-compatible dictionary with optional list defaults. Do not mutate inputs. |
| `load_inventory(path)` | Read an explicit UTF-8 path and return the same normalized dictionary. Do not modify the source file. |
| `resolve_targets(inventory, *, home_id, selector)` | Return exactly `{"area_ids": [...], "device_ids": [...]}`, sorted and unique, without mutating inputs. |
| `InventoryError` | Validation exception with a nonblank explanation and `.path`, a sequence of field names/list indices. Inventory paths start at the envelope; selector paths start with `selector`, and Home mismatch uses `home_id`. |

Error tests use single-fault mutations and repeat the same call to establish
location stability. A duplicate ID identifies the later object in envelope
order (Home/Floors/Areas/Devices/Labels/Area-groups); a duplicate list member
identifies its later index. Invalid selector form uses `("selector",)`.
These conventions make diagnostics reviewable without depending on a particular
validation library's prose or object models.

The CLI seam is:

```bash
python -m state_schema.home_inventory PATH
```

Success emits normalized JSON to stdout and exits zero. Failure exits nonzero,
leaves stdout empty and explains the file/cause on stderr, with a field path
where applicable. The [example instructions](../../../docs/product/home-intelligence/examples/README.md)
document installation, private edits and runtime validation.

## Offline guards and evidence

An autouse parent guard denies socket connections/DNS and child process creation.
Resolver purity cases also deny common filesystem write/mutation paths. CLI tests
launch the real command with a child `sitecustomize` audit hook that denies socket
events, process execution and filesystem mutation. The hook records attempts
before raising; swallowed guard exceptions therefore fail the parent assertion.
Bytecode writes are disabled. Infrastructure tests exercise
those guards and the real Git ignore rule even while runtime TCs skip.

These guards cover Python's audited/standard-library paths; they do not provide
an OS sandbox against native code or preopened descriptors. There are no live
provider/action entry points in this slice to spy on. If implementation introduces
any, its TC review must add direct spies on those real entry points as well.
No absent provider implementation is mocked into existence here.

Use `--require-inventory-runtime`: absent runtime aborts the run, and any
remaining skip makes the run unsuccessful. CI requires this mode. An ordinary
run retains module-absence skip markers for the test-first workflow, but cannot
establish acceptance when any case skips.

For runtime acceptance record the tested commit, Python/dependency versions,
command and complete pass/fail/skip counts in the linked Harness TCs. All runtime
skips must be resolved before claiming acceptance. On root-only environments the
unreadable-file case skips because root bypasses mode bits; run that case as an
unprivileged user before approval. Applicable lint/type checks and governance
gates must also pass. TC code review and runtime acceptance are separate handoffs.

## REQ-014 ProviderBinding acceptance tests

TC-014-01–06 are implemented against `state_schema.provider_binding`, with
fictional HA/mock resource strings and the separate before/after fixture.
PR #29 is merged; human-001 accepted the combined delivery and TC-014-01–06
are passing. Final disposition is recorded in the REQ-014 closeout evidence.

Run both sets of required contracts:

```bash
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime -q
```

The binding acceptance option fails if the module is absent or any test skips.
Module absence is the only pre-implementation gate; missing exports or broken
imports fail. New tests exercise real shape/collection factories, typed snapshot
isolation, precise failure paths and privacy, reference/collision rules and full
inventory/target equality across replacement. Parent socket/DNS/process guards
apply to all cases; the pure-validation case also blocks filesystem writes.
The guards cover standard Python entry points, not native code or an OS sandbox.
No provider service is mocked into existence or dispatched by this suite.

## REQ-015 Canonical State acceptance tests

TC-015-01–06 exercise the real `state_schema.canonical_state` factories,
collection validation, partial updates and derived convergence. The public
API and exact error path conventions are recorded in REQ-015. Fixtures are
fictional; no provider or dispatcher is mocked into existence. Tests cover
strict scalar/time/reference handling, type-preserving unavailable values,
per-member stale/replay/conflict decisions, epoch fencing, separate intent
revisions and ACK-only versus physically observed agreement.

```bash
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime -q
```

State acceptance mode fails on absent runtime and any skip. Isolated subprocess
cases exercise those failure gates. Parent network/DNS/process guards apply
throughout; pure contract tests also deny common filesystem mutations.
PR #31 merged as `58f411e`; human-001 accepted all six State TCs under the
explicit merge disposition. REQ-015 is archived done; no evaluator signature
is inferred from author self-checks.

## Pre-review portability and guard revision

State CI uses Python 3.12, 3.13 and 3.14. Its workflow runs lint/type, required
runtime tests, fixture/legacy checks and built/installed-wheel smoke; these are
separate automated steps, not all assertions in TC-015-06's unit-test file.
Parent guard evidence uses a private counter exposed through a read-only getter;
only infrastructure probes predeclare expected denied attempts via marker.
The fixture exposes no mutable list or clearing method. Socket/DNS, subprocess
and available `os.system`/fork/exec/spawn paths are patched; swallowed attempts
still fail teardown. This is reviewed test instrumentation, not protection
against intentionally modified tests, monkeypatches, native code or preopened
descriptors. Filesystem guards tolerate unavailable OS methods.

## REQ-016 Capability acceptance tests

TC-016-01–06 exercise real descriptor/catalogue factories, strict text ingestion,
bounded schema/payload validation, action metadata and completion references.
Q1–Q5 clarify duplicate-key handling, structural equality, independent depth
counts, 2–4 segment IDs and exact interaction text limits. The ACK timeline
calls the existing REQ-015 State helper; it creates no task/event executor.

```bash
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime -q
```

Absent Capability runtime and any required skip fail acceptance; isolated actual
pytest probes demonstrate both. Parent network/DNS/process guards apply, and
pure contract cases additionally deny filesystem mutations on success/failure,
including environments with missing OS methods. CI runs the full package,
lint/type and installed-wheel smoke on Python 3.12/3.13/3.14. These are author
self-checks, distinct from later human final acceptance: PR #32 is merged and
TC-016-01–06 are passing under the human merge disposition. See REQ-016 closeout evidence.

## REQ-017 Initial Capability acceptance tests

TC-017-01–06 exercise all six packaged definitions through
`state_schema.initial_capabilities.load_initial_capabilities`, the existing
Capability payload validators and actual State helpers. Required mode distinguishes
this slice from the already-present base Capability module:

```bash
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime -q
```

Module absence fails fast; a missing/malformed resource or broken accessor fails
actual tests, and any skip fails required acceptance. Resource fault injection
replaces only the read boundary, leaving real decoding/validation intact. Tests
cover fixed machine schemas, units, metadata, sensor read-only selection, detached
snapshots and private diagnostics; no provider or task service is invented.
A subprocess verifies import performs no catalogue read; explicit retrieval allows
only the fixed package read while denying writes/clocks/environment discovery.
All parent network/process guards remain active, including swallowed effects.
Source import probes explicitly use this checkout's source path on every interpreter;
installed-wheel smoke separately runs with `-I` from `/tmp` and imports the wheel.

CI runs all five required-runtime options on Python 3.12/3.13/3.14 plus lint/type
and installed-wheel smoke that reads all six definitions. Build evidence also
checks the JSON resource in wheel and sdist. This is implementation evidence;
TC-017-01–06 stay implemented and independent acceptance remains pending.
