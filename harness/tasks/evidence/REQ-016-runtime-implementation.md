# REQ-016 — Combined TC and Runtime Self-check Evidence

Authority: [REQ-016](../features/REQ-016.md). Human-001 explicitly authorized implementation through req_impl and requested external review afterward. This records Generator self-checks, not independent T07/T10/T13 approval. TC-016-01–06 remain implemented and AC1–AC7 remain unchecked.

## Verification Boundary

Linux aarch64, non-root UID 1000. No provider credentials, live service, device or dispatcher. The DSH PR #32 pre-review of `7405541e` remains human-supplied non-signing Termux / CPython 3.14.6 evidence for the original documentation artifact, not verification of this later Capability runtime.

## Artifact and Local Environment

Source/test artifact: `4c400c75655e790aa93e758b149a3d427e936435`. The following final-source checks ran immediately before that commit with no subsequent source/test changes. Linux aarch64 / non-root UID 1000, CPython 3.12.12 and 3.14.3, pytest 9.1.1. Ruff 0.16.10 and strict mypy 2.4.0 (all five source files) pass on the 3.12 tool environment. No author-performed Termux or CPython 3.14.6 run is claimed.

Test-first: 957 existing cases passed, 237 initial Capability cases skipped only because the module was absent. Required mode returned failure on skips; `--require-capability-runtime` returned exit 4 with the missing-runtime error. Boundary tests were expanded to 315 before final delivery. Final required mode executes all cases.

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime -q --junitxml=/tmp/req016-results.xml
/tmp/req015-py314-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime -q --junitxml=/tmp/req016-py314-results.xml
/tmp/req014-env/bin/ruff check libs/state-schema/src libs/state-schema/tests
/tmp/req014-env/bin/mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
python3 tools/check_home_intelligence_requirements.py
git diff --check
```

## Per-TC Execution

Both CPython 3.12.12 and 3.14.3 execute **1272 passed, zero skipped/failed**.

| Scope | Passed per interpreter | Skipped | Failed |
|---|---:|---:|---:|
| TC-016-01 identity/text/catalogue/isolation | 102 | 0 | 0 |
| TC-016-02 schemas/payload/depth | 113 | 0 | 0 |
| TC-016-03 action metadata | 39 | 0 | 0 |
| TC-016-04 completion references/equality | 39 | 0 | 0 |
| TC-016-05 ACK/physical evidence | 17 | 0 | 0 |
| TC-016-06 offline/absence/skip gates | 5 | 0 | 0 |
| Existing inventory/binding/State/guards | 957 | 0 | 0 |

315 Capability cases include 312 cases executing the actual public validators/helpers and three static/isolated-acceptance probes (module boundary and two actual pytest gate subprocesses). Guards do not simulate provider execution. The ACK timeline validates actual accepted output and uses the real State helper; observation evidence remains separate.

Q1 is exercised at pure text ingestion with duplicate keys nested in an otherwise valid descriptor; a normal caller decoder demonstrably loses those keys. Q2 covers key order, list order, omitted/explicit bounds and bool/numeric distinctions. Q3 counts schema and payload trees independently at 16/17, including a valid deeply nested schema inside JSON descriptor wrappers and cyclic/deep inputs. Q4 tests 2–4 segments and per-segment bounds. Q5 tests descriptor and all interaction title/description endpoints.

## Packaging and Automation

Offline `uv build --offline --cache-dir /tmp/ai-family-uv-cache --out-dir /tmp/req016-dist libs/state-schema` builds wheel and sdist with existing cached build dependencies. No runtime dependency is added. Install that wheel with `uv pip install --offline --no-deps` into fresh `/tmp/req016-wheel-env` (CPython 3.12.12) and `/tmp/req016-wheel314-env` (3.14.3), then from `/tmp` run each interpreter with `-I` against committed `libs/state-schema/tests/wheel_smoke.py`. Both pass: installed-module path, actual catalogue/text/payload APIs, exact-version failure, duplicate-key/unsupported-reference rejection, State ACK rejection and observed convergence/epoch fencing. This smoke imports the installed wheel, not source-path injection.

CI requires all four runtime flags on Python 3.12/3.13/3.14, lint/type, public-data/legacy checks and built/installed-wheel smoke. Governance and all 21 planning regressions pass locally. CI results are recorded below after completion; local self-checks do not substitute for independent review.

## Review Limits

Factories validate external input; direct dataclass constructors remain internal typed records. Public payload/lookup methods revalidate snapshots. Shape-valid positive capability revisions are not proof of semantic consumer support; exact catalogue lookup never upgrades. Schema equality is conservative and has no semantic subsumption. The 16-node limits bound depth, not total document breadth. Text decoder resource limits may reject exceptionally nested input before validation. Dict boundaries cannot recover discarded duplicate keys.

Risk/idempotency/timeout/completion metadata runs no task engine, deadline, deduplication, event correlation, provider client, authorization or dispatch. Event schema validity alone is insufficient task correlation. State-converged references do not update State or allocate intent epochs/baselines. Offline Python guards cover standard instrumented network/process/write paths, including swallowed attempted effects, but do not establish an OS/native-code sandbox. No full WoT conformance, six production capability schemas or physical-device certification is claimed.

## Implementation CI and Stop Boundary

[CI run 37881889833](https://github.com/rushwing/ai-family/actions/runs/37881889833), evidence head `7556f67`, passes all eight applicable jobs: governance-gates, changes, req002-integration, goal-agent, mcp-toolsets, and state-schema-tc for Python 3.12/3.13/3.14. Each contract matrix job runs lint/type, zero-skip required tests, fixture/legacy checks and installed-wheel smoke. Web/workbook jobs skip by path filtering; legacy checks still execute in the matrix. Runtime artifact remains `4c400c7`.

T12 ends req_impl and hands off req_impl_review / evaluator-001 for the external combined review human-001 will arrange. PR #32 stays draft, TC-016-01–06 stay implemented and AC1–AC7 stay unchecked. No author self-approval, ready, merge or further implementation follows this handoff. Final documentation has a separate CI run and does not alter runtime evidence.

## Human-supplied Local Pre-review and Authorized Repairs

[human-001][2026-10-09] Supplied the non-signing PR #32 local pre-review of `4bad1aca` and instructed resuming to fix its findings. That reviewer reports 1272 passed on Android/Termux aarch64 / CPython 3.14.6, governance/21 planning regressions and isolated installed-wheel smoke passed, with no blocking findings. Ruff/mypy were checked through CI rather than run on Termux. This is attributed reviewer evidence for the prior revision, not an author-performed run and not T03/T07/T10/T13 approval. It does not verify the repaired revision below; the additional independent adversarial review mentioned in the supplied report has not been supplied.

| Finding | Disposition |
|---|---|
| P2/F-1: root payload bound failures have empty paths | Fixed: numeric/length failures now append the violated constraint keyword to the value-node path, e.g. `("maxLength",)` at root or `("value", "minItems")` for a nested array. Nested member/index locations are retained; no submitted values are exposed. |
| Information/F-2: fixed duplicate-key path cannot locate nested duplicates | Explicitly documented in the specification and package README: object-pairs hooks supply no containing path, so every duplicate-key error uses `("<unknown>",)` without exposing the key. |
| Information/F-3: implicit capability ID length bound | Explicitly documented in Q4 and the README: at most 131 characters, from four 32-character segments plus three dots. |
| Information/F-4: combined closeout/specification/runtime PR | Retain the combined delivery already authorized by human-001. This informational observation identifies no correctness defect or requirement to split the PR. |
| Information/F-5: defensive schema snapshot/revalidation cost | Retain revalidation at public boundaries, including internally constructed typed records. The reviewer reports no practical descriptor-scale impact; no performance optimization or benchmark claim is made. |

Repair source/test artifact: `a682623`. Linux aarch64, UID 1000, CPython 3.12.12 and 3.14.3 / pytest 9.1.1. Added 24 cases covering integer/number minimum/maximum and string/array minimum/maximum lengths at root, object member and array element locations through both `Schema.validate` and `validate_payload`. Every case checks deterministic exact paths, privacy and unchanged input/record snapshots. All 24 failed before the fix and pass afterward.

Both interpreters pass **1296 tests, zero failed/skipped**: 339 Capability cases (336 public-validator/helper cases plus the same three static/acceptance probes) and 957 existing cases. Per-TC counts are **102 / 137 / 39 / 39 / 17 / 5** for TC-016-01–06. JUnit results: `/tmp/req016-review-fixes-py312.xml` and `/tmp/req016-review-fixes-py314.xml`. The four required-runtime flags remain enabled.

Ruff and strict mypy (five sources), governance/all 21 planning regressions, public-data, legacy requirements and whitespace checks pass. Offline wheel/sdist build to `/tmp/req016-review-fixes-dist` passes; fresh isolated installations into `/tmp/req016-review-wheel312` and `/tmp/req016-review-wheel314` both pass committed `wheel_smoke.py` with `-I` from `/tmp`. No author Termux/3.14.6 run is claimed for the repair.

REQ-016 remains `req_impl_review` / evaluator-001, all six TCs remain implemented and AC1–AC7 unchecked. PR #32 stays draft for independent combined review; no readiness, queue approval or merge disposition is inferred from this non-signing report.
