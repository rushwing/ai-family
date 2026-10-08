# REQ-013 acceptance tests

TC-013-01–07 implement the reviewed acceptance text. The shared inventory package
is still unimplemented. Tests call the eventual public API directly and never
substitute a fake validator, loader or resolver. Missing runtime modules produce
explicit skips; broken imports or missing exports in an existing module fail.
The seven guard checks are test-infrastructure checks, not AC1–AC7 acceptance.

Run from the repository root with Python 3.12+ and pytest:

```bash
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests -q
```

The isolated pytest configuration adds `libs/state-schema/src` to the import
path and does not collect unrelated service integration tests. Runtime
implementation should supply its own package metadata and validation dependency;
this test-only delivery selects neither a validation library nor runtime models.

## Public test seam

The eventual `state_schema.home_inventory` module must expose these JSON-facing
functions. Internal typed models and validation libraries remain implementation
choices. If an implementation review selects another equivalent public API,
adapt the test seam without weakening the assertions and record that review.

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

This is a required future command, not an existing loader. Success emits the
normalized JSON to stdout and exits zero. Failure exits nonzero, leaves stdout
empty and explains the file/cause on stderr, with a field path where applicable.
The future example instructions must document this delivered command before
runtime acceptance.

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

Use `--require-inventory-runtime` for acceptance: absent runtime aborts the run,
and any remaining skip makes the run unsuccessful. The ordinary test-first CI
mode preserves explicit skips until implementation lands.

For runtime acceptance record the tested commit, Python/dependency versions,
command and complete pass/fail/skip counts in the linked Harness TCs. All runtime
skips must be resolved before claiming acceptance. On root-only environments the
unreadable-file case skips because root bypasses mode bits; run that case as an
unprivileged user before approval. Applicable lint/type checks and governance
gates must also pass. TC code review and runtime acceptance are separate handoffs.
