# REQ-015 — Combined TC and Runtime Self-check Evidence

Date: 2026-10-09. Authority: [REQ-015](../archive/done/features/REQ-015.md).
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

On Linux aarch64 / CPython 3.12.12, 942 passed with zero skips/failures. Of the 228 State cases, 225 directly exercise the public seam and three are static boundary/acceptance-gate checks. This is historical evidence for the original artifact; the pre-review revision below supersedes it. Tests preserve scalar types and empty/literal strings, reject unsupported versions/types/UTC dates, protect nested snapshots, validate Home/Device references, isolate per-member ordering, fence generations, detect typed replay conflicts and require eligible post-baseline observations. The public ACK timeline demonstrates unknown → pending → confirmed with false/zero agreement. An acknowledged-only command supplies no State update.

The autouse parent guard rejects socket/DNS/process effects; the pure-contract test additionally denies common filesystem mutations, including on failure paths. Isolated actual pytest subprocesses confirm absence and skipped required cases make State acceptance fail. Import/API checks reject store/provider/dispatch imports. These are Python instrumentation boundaries, not an OS-level sandbox or native-code guarantee.

Ruff passes; strict mypy passes for all four source files. Governance gates and all 21 planning regressions pass. Public-data, legacy requirements and whitespace checks pass. CI now requires all three runtime options and publishes shared JUnit results.

## Package Verification

`uv build --cache-dir /tmp/ai-family-uv-cache --out-dir /tmp/req015-dist libs/state-schema` built the wheel and source distribution. The initial sandbox network denial was retried with approved access to resolve the existing hatchling build dependency. No runtime dependency was added.

Installed the wheel without dependencies into `/tmp/req015-wheel-env`, then ran `/tmp/req015-wheel-smoke.py` from `/tmp`. The module path confirms the installed wheel rather than the editable checkout. Reference validation and actual update/convergence APIs yield unknown after ACK, pending after mismatch, confirmed after matching false/zero reports, and reject old-generation updates. This proves packaging/import and public helper behavior, not a live provider integration.

## Review Boundary

The package has no store, provider client, action/task runtime, clock/TTL allocator, persisted epoch generator or device write path. Caller-supplied generation context must be retained by the future owner; stateless checks only detect rollback against epochs in the submitted snapshot. Null update arguments mean no update; revisionless intent cancellation is excluded. Direct dataclass constructors remain internal typed records; external boundaries use factories. Unknown structural/property keys are redacted in diagnostics while valid property names remain in paths.

TC-015-01–06 stay implemented and AC1–AC7 stay unchecked until independent combined text/code/feature review accepts them. No passing/complete State lifecycle or independent review signature is inferred from these self-checks.

## Implementation CI and Handoff

[CI run 37872795653](https://github.com/rushwing/ai-family/actions/runs/37872795653), head `8be63cd`, passed all six applicable jobs: governance-gates, changes, req002-integration, state-schema-tc, goal-agent and mcp-toolsets. The unrelated web/workbook jobs were skipped by path filtering; required contract execution had zero skips. [Draft PR #31](https://github.com/rushwing/ai-family/pull/31) holds the combined review. T12 hands off REQ-015 to `req_impl_review` / evaluator-001. Final handoff documentation receives its own CI run; this historical run verifies the implementation/evidence artifact.

## Local Pre-review Revision

Human-001 supplied DSH's non-signing pre-review of head `0862d16`: Termux /
CPython 3.14.6 recorded 938 passed, 4 failed, zero skips. This is reported
external evidence, not independently reproduced Termux execution here, and
supplies no T07/T10/T13 approval. The original Linux 3.12 counts above remain
historical and must not be read as a portable success claim.

Revised source/test artifact: `1356e1e`. Locally reproduced the parser difference:
CPython 3.14.3 turns `2026-01-01T24:00:00+00:00` into the next day's midnight;
3.12.12 raises ValueError. State now range-checks hours/minutes/seconds before
calendar parsing. A permissive-parser regression prevents dependency on that
interpreter behavior. No supported-Python upper bound was added.

| Feedback | Revision/disposition |
|---|---|
| F1 | Explicit clock ranges; unchanged invalid-date/UTC syntax rejection; CI expands to Python 3.12/3.13/3.14. |
| F2 | Shared schema-derived inventory-path sanitizer in State and Binding wrappers: unknown keys become `<unknown>`, fields/indices survive; value and exception-chain suppression remain. Home/Device/root-key privacy regressions added. Legacy inventory validator paths remain unchanged. |
| F3 | Parent guard exposes a counter reader, not a mutable list; expected infrastructure attempts are predeclared. Available os.system/fork/exec/spawn APIs are denied. Actual isolated pytest probes swallow denied calls and still fail teardown. Test instrumentation does not resist actively rewritten tests or Python introspection. |
| F4 | Filesystem guards tolerate absent OS methods; State/Binding purity cases explicitly simulate absent os.link. Existing inventory purity guard updated consistently. |
| F5 | Success statements identify interpreter/OS; no Termux or Python 3.14.6 retest is claimed. |
| F6 | Real helper rejects ACK keyword arguments and raw ACK through observation/availability boundaries; exact helper parameters are asserted. The timeline now executes a rejected ACK call, instead of a no-update identity assertion. |
| F7 | CI matrix runs lint/type, required runtime, public-data/legacy checks, wheel build and isolated installed-wheel smoke. Governance/planning remains its separate job. TC-015-06 now identifies pytest versus CI automation explicitly. |
| F8 | Existing stateless epoch ownership limitation retained. |
| F9 | Specification confirms current-generation online availability may predate intent; strict post-baseline ordering applies to desired reports. Regression added; TTL inference remains excluded. |
| F10 | Original count corrected: 225 public-seam cases plus three static/gate cases. Revised State suite has 238 cases, of which 234 exercise the public seam and four check static boundaries/gates/shared ID authority. |
| F11 | All inventory/binding/state canonical ID validators share home_inventory.CANONICAL_ID_PATTERN; identity consistency test added. |

### Revised Local Verification

On Linux aarch64, non-root UID 1000, **both CPython 3.12.12 and 3.14.3** with
pytest 9.1.1 pass **957 tests, zero skips/failures**. Commands use the same
required three-runtime pytest options as above, with JUnit artifacts
`/tmp/req015-revision-results.xml` and `/tmp/req015-revision-py314-results.xml`.
The final strengthened ACK timeline also passes all 37 TC-015-05 cases on both.

| Scope | Passed per interpreter | Skipped | Failed |
|---|---:|---:|---:|
| TC-015-01 | 137 | 0 | 0 |
| TC-015-02 | 17 | 0 | 0 |
| TC-015-03 | 19 | 0 | 0 |
| TC-015-04 | 23 | 0 | 0 |
| TC-015-05 | 37 | 0 | 0 |
| TC-015-06 | 5 | 0 | 0 |
| Existing inventory/binding and expanded guard infrastructure | 719 | 0 | 0 |

Ruff 0.16.10, strict mypy 2.4.0 (four sources), governance/21 planning regressions,
public-data, legacy requirements and whitespace checks pass locally. Offline
wheel/sdist rebuild succeeded in `/tmp/req015-revision-dist`. Reinstalled the
wheel without dependencies, then ran the committed `tests/wheel_smoke.py` from
`/tmp` with `-I` on both interpreters: installed-module path, reference validation,
ACK rejection, observed false/zero agreement and epoch fencing passed.
These local commands remain Generator self-check evidence.

### Revised CI and Handoff

[CI run 37875942512](https://github.com/rushwing/ai-family/actions/runs/37875942512),
head `a80216f`, passes all eight applicable jobs: governance-gates, changes,
req002-integration, goal-agent, mcp-toolsets and state-schema-tc for Python
3.12/3.13/3.14. Each State job runs lint/type, required runtime tests,
public-data/legacy validation and the built/installed-wheel smoke on GitHub's
ubuntu-latest runner. Path-filtered web/workbook jobs skip; legacy validation
still runs in the State matrix. Revised T12 returns REQ-015 to
`req_impl_review` / evaluator-001. Final documentation gets its own CI run.
PR #31 remains draft; no independent approval, passing TC status or accepted
AC checkboxes are inferred from these self-checks.

## Human-supplied Second-round Verification and Merge Disposition

On 2026-10-09 human-001 supplied DSH's second-round local pre-review of `31ef0988cf49660827925e7f4a1dedcbad0f73eb`. Reported environment: Android/Termux aarch64, CPython 3.14.6, pytest 9.1.1. Required acceptance: 957 passed, zero failed/skipped; State counts 137/17/19/23/37/5 (238 total). Governance and 21 planning regressions passed. `pip wheel` and isolated installed-wheel `python -I tests/wheel_smoke.py` passed; Termux used virtualenv because ensurepip was unavailable. DSH checked final CI run 37876129251 and the 3.14 job's lint/type/runtime/public-data/legacy/wheel steps. Local Termux Ruff/mypy execution remained unavailable. These are human-supplied external results, not author-performed Termux runs.

DSH confirms F1–F7 fixed, F8–F11 disposed as documented, and no new blocking findings. Its report explicitly supplies no registered independent T07/T10/T13 signature. The remaining informational request to trace the REQ-014 diagnostic change is recorded in REQ-014-review-acceptance.md.

Human-001 then explicitly instructed checking for any further amendments and merging PR #31. This is the human final acceptance/merge disposition, superseding the pending handoff for this delivery; it does not turn DSH's report or Generator self-checks into independent evaluator signatures. AC1–AC7 are accepted and TC-015-01–06 marked passing under that human disposition. No code changes are needed following round two.

## Merge and Closeout

PR #31 merged as `58f411edf7199ede236f274632b77b73d08bed02` on 2026-10-09. REQ-015 is archived done under human-001's explicit final disposition. Historical pending-review statements above are superseded. [Closeout evidence](REQ-015-review-acceptance.md) records merge provenance and the post-merge offline verification; no new independent review signature is claimed.
