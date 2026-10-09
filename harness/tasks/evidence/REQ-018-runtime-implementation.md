# REQ-018 Runtime Implementation Evidence

## Authority and Boundary

Human-001 explicitly authorized PR #36 merge and combined TC design/code/runtime implementation, stopping after req_impl for external review. PR #36 merged as `a87d235b5193f8b4ad5137c5018f9792895b0994`. Requirement scope approval derives from that human disposition; the supplied Termux pre-review is non-signing. This evidence is generator-001 self-check, not independent T07/T10/T13 acceptance. AC1–AC8 remain unchecked and TC-018-01–06 implemented. No implementation merge or readiness is authorized.

## Artifacts and Environments

Test-first artifact: `34e51b6`, no action runtime. Before runtime creation, Linux aarch64 / CPython 3.12.12 passed 1493 baseline tests with 270 explicitly skipped new cases; `--require-action-runtime` failed with exit 4 and the missing-runtime error. Final tests add 32 cases/parametrizations and privacy/packaging coverage; those additions do not alter the recorded historical absent-runtime counts.

Final source/test/runtime/CI artifact: `c6e2ce5` (content tested before its commit, then recorded unchanged). Local environments: Linux aarch64 / CPython 3.12.12 (`/tmp/req014-env/bin/python`) and CPython 3.14.3 (`/tmp/req015-py314-env/bin/python`). Both execute 1795 passed, zero failed/skipped, including all 302 new Action cases. Python 3.13 is verified by CI, not claimed as a local run. The earlier Android/Termux 3.14.6 pre-review belongs to the specification baseline, not this runtime.

| TC | Runtime test file | Passed on each local interpreter | Failed/skipped |
|---|---|---:|---:|
| TC-018-01 | test_action_contracts_01.py | 118 | 0/0 |
| TC-018-02 | test_action_contracts_02.py | 12 | 0/0 |
| TC-018-03 | test_action_contracts_03.py | 98 | 0/0 |
| TC-018-04 | test_action_contracts_04.py | 36 | 0/0 |
| TC-018-05 | test_action_contracts_05.py | 26 | 0/0 |
| TC-018-06 | test_action_contracts_06.py | 12 | 0/0 |

Counts come from `/tmp/req018-py312-results.xml` and `/tmp/req018-py314-results.xml`; prior inventory/binding/State/Capability/catalogue regressions remain 1493. Local JUnit files are temporary evidence, not shipped resources.

## Commands and Results

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime \
  -q --junitxml=/tmp/req018-py312-results.xml
/tmp/req015-py314-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime \
  -q --junitxml=/tmp/req018-py314-results.xml
/tmp/req014-env/bin/ruff check libs/state-schema/src libs/state-schema/tests
/tmp/req014-env/bin/mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
python3 tools/check_home_intelligence_requirements.py
git diff --check
```

All pass; strict mypy checks seven source files. Governance includes all 21 planning regressions. Pure-call tests deny file/network/process/clock/environment access, track attempted effects including swallowed errors, and validate input isolation. These Python guards cover common entry points, not native code or an OS security sandbox. Import audit allows module source/bytecode reads but no application resource I/O. Required-gate subprocesses exercise actual pytest session hooks for absent Action module and required skips.

## Packaging

`uv build --cache-dir /tmp/ai-family-uv-cache --out-dir /tmp/req018-dist libs/state-schema` builds wheel from sdist. Both archives contain action_contracts.py, py.typed and the existing initial_capabilities.v1.json; wheel module bytes equal the tested source.

- Wheel SHA-256: df9ccde21a2671ef57acd9ecf7a31fd813b6553a9367c031e32d4570b9ec397a
- Sdist SHA-256: e8cb80554a7b75cdbc12508b694b094965867da2fd0ca54aeedd157372a08df8

Fresh `/tmp/req018-wheel312-env` and `/tmp/req018-wheel314-env` virtualenvs install only this wheel with no runtime dependencies. From `/tmp`, both execute `python -I /home/openclaw/.openclaw/workspace/ai-family/libs/state-schema/tests/wheel_smoke.py` successfully. The smoke asserts installed paths under each virtualenv, validates Request/Task/Result, rejects ACK-as-success, confirms a real observed false target and classifies trace-only replay while retaining existing State/Capability/catalogue checks. Installed-wheel code is isolated from the source tree; fictional example files are explicit smoke inputs.

## Behavior and Practical Limits

Pure contracts strictly validate canonical identity/revision, explicit requester Home and real typed input/output; no validation confers authentication, permission, Device support or confirmation. Type-exact scoped idempotency deliberately differs from Capability numeric enum equality. Every legal/illegal transition pair is exercised; stored success claims undergo contextual evidence validation. Running context is caller-established and frozen through transitions. ACK has only unverified acknowledged semantics under ack_only, event success requires exact correlated current-generation post-baseline payload, and State success Capability-validates every known target report before calling actual State convergence with descriptor-derived intent.

Shape-only factories and trusted persisted snapshots cannot establish authenticity or historical provenance. A service must protect context/evidence/Task storage before using these helpers. Conflicting same-state Result replay rejects; this is not a mutable progress-event or transport-telemetry store. Cancellation/timeout do not prove rollback or safe retry. There is no provider, dispatch, durable concurrency/restart idempotency, timer, audit or auth service in this slice. HI-S025 and guarded write integration remain future work.

## External Review Handoff

Independent combined review of TC text/code and runtime remains pending. CI result and draft implementation PR linkage are recorded in the REQ after final-head verification. No evaluator signature or completed status is inferred from these results.
