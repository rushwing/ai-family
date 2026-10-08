# REQ-013 acceptance tests

TC-013-01–07 implement the reviewed acceptance text against the delivered
inventory package. Tests call the public API directly and never substitute a
fake validator, loader or resolver. Frozen-record and strict JSON decoding
regressions supplement the original TC code. The seven guard checks are
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
Bytecode writes are disabled. Seven independent infrastructure tests exercise
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
Independent TC text/code and feature review is deferred to PR #29 under the
explicit instruction to prepare one combined review. TCs remain `implemented`
until that review; test execution alone does not confer acceptance.

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
