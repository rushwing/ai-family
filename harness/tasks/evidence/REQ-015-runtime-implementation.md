# REQ-015 — Combined TC and Runtime Self-check Evidence

Date: 2026-10-09. Authority: [REQ-015](../features/REQ-015.md).
Human-001 explicitly requested merging PR #30 and starting REQ-015. PR #30
merged as `09f1abd`; scope approval and combined-delivery sequencing are recorded
in the REQ. These are Generator self-checks, not independent T07/T10/T13 approval.

## Tested Artifact and Environment

Implemented feature/test commit: `9a67881` (`feat(REQ-015): implement strict offline canonical State contracts`). Linux aarch64, Python 3.12.12, pytest 9.1.1, Ruff 0.16.10, mypy 2.4.0; non-root UID 1000, editable package in `/tmp/req014-env`. No HA endpoint, provider credentials, physical device or action dispatcher.

Test-first run before State delivery: 714 existing cases passed, 190 State cases skipped solely because the module was absent. `--require-state-runtime` returned exit 4 with the missing-runtime diagnostic. Additional negative/boundary cases were added before runtime verification. Required acceptance mode now executes every case.

## Runtime Execution

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime -q \
  --junitxml=/tmp/req015-results.xml
/tmp/req014-env/bin/ruff check libs/state-schema/src libs/state-schema/tests
/tmp/req014-env/bin/mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
python3 tools/check_home_intelligence_requirements.py
git diff --check
```

| Scope | Passed | Skipped | Failed |
|---|---:|---:|---:|
| TC-015-01: shapes/references/isolation | 130 | 0 | 0 |
| TC-015-02: unknown/offline versus false/zero | 17 | 0 | 0 |
| TC-015-03: member ordering/replay/conflicts | 19 | 0 | 0 |
| TC-015-04: epoch fencing/intent revision | 23 | 0 | 0 |
| TC-015-05: convergence/ACK timeline | 35 | 0 | 0 |
| TC-015-06: offline/absence/skip gates | 4 | 0 | 0 |
| Existing inventory/binding/guards | 714 | 0 | 0 |

942 passed, zero skips/failures. All 228 State cases call the delivered factories/helpers. Tests preserve scalar types and empty/literal strings, reject unsupported versions/types/UTC dates, protect nested snapshots, validate Home/Device references, isolate per-member ordering, fence generations, detect typed replay conflicts and require eligible post-baseline observations. The public ACK timeline demonstrates unknown → pending → confirmed with false/zero agreement. An acknowledged-only command supplies no State update.

The autouse parent guard rejects socket/DNS/process effects; the pure-contract test additionally denies common filesystem mutations, including on failure paths. Isolated actual pytest subprocesses confirm absence and skipped required cases make State acceptance fail. Import/API checks reject store/provider/dispatch imports. These are Python instrumentation boundaries, not an OS-level sandbox or native-code guarantee.

Ruff passes; strict mypy passes for all four source files. Governance gates and all 21 planning regressions pass. Public-data, legacy requirements and whitespace checks pass. CI now requires all three runtime options and publishes shared JUnit results.

## Package Verification

`uv build --cache-dir /tmp/ai-family-uv-cache --out-dir /tmp/req015-dist libs/state-schema` built the wheel and source distribution. The initial sandbox network denial was retried with approved access to resolve the existing hatchling build dependency. No runtime dependency was added.

Installed the wheel without dependencies into `/tmp/req015-wheel-env`, then ran `/tmp/req015-wheel-smoke.py` from `/tmp`. The module path confirms the installed wheel rather than the editable checkout. Reference validation and actual update/convergence APIs yield unknown after ACK, pending after mismatch, confirmed after matching false/zero reports, and reject old-generation updates. This proves packaging/import and public helper behavior, not a live provider integration.

## Review Boundary

The package has no store, provider client, action/task runtime, clock/TTL allocator, persisted epoch generator or device write path. Caller-supplied generation context must be retained by the future owner; stateless checks only detect rollback against epochs in the submitted snapshot. Null update arguments mean no update; revisionless intent cancellation is excluded. Direct dataclass constructors remain internal typed records; external boundaries use factories. Unknown structural/property keys are redacted in diagnostics while valid property names remain in paths.

TC-015-01–06 stay implemented and AC1–AC7 stay unchecked until independent combined text/code/feature review accepts them. No passing/complete State lifecycle or independent review signature is inferred from these self-checks.
