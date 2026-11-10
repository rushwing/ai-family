# REQ-036 independent review handoff

Historical implementation/review record. The later human final disposition in
[final acceptance](REQ-036-review-acceptance.md) supersedes pending approval
and req_impl stopping statements below; source-specific evidence remains historical.

Prepared on 2026-11-10 for [draft PR #74](https://github.com/rushwing/ai-family/pull/74).
The review baseline is `98cb612347cb2450fb612aa7e36aff8820a86e4d`, against
`e4216354fbef5674538b75e7c7bd274579fabc7b`. This handoff adds review navigation;
it does not change runtime, tests or the baseline's verification scope.

The [second-round repairs](REQ-036-second-round-fixes.md) document the later
copy/deepcopy regression coverage and its verification. The baseline evidence
below remains source-specific historical evidence; it does not certify those
later test bytes.

## Authority and current state

The sole [REQ-036](../archive/done/features/REQ-036.md) remains `req_impl / generator-001`,
with AC1–AC5 unchecked. Human-001 authorized implementation and “fix all
findings”; generator repairs address the supplied T1/F1–F6 pre-review.
All four TC documents remain generator-authored drafts. Independent TC
design/review and implementation acceptance are pending. This packet supplies
no evaluator signature or lifecycle transition. On 2026-11-10 GitHub reported
the PR open/draft and returned no review comments or submissions.

## Review order and criteria

First review or revise the draft TC criteria independently of their current
implementation mappings. Passing generator probes cannot establish that the
criteria are complete. Then assess the implementation against the approved
criteria and REQ ACs, recording any missing cases or implementation defects.

| Draft criteria | AC coverage | Review focus | Recorded passing mappings |
| --- | --- | --- | --- |
| [TC-036-01](../test-cases/TC-036-01.md) | AC1, AC2, AC5 | Complete single-entity projection; strict timestamp filtering before rebasing; deduplication, removals and remaps | 11 |
| [TC-036-02](../test-cases/TC-036-02.md) | AC1, AC2, AC5 | Atomic complete-home publication; current intent preservation; strict epoch floor; repeat reconnect and racing reads | 6 |
| [TC-036-03](../test-cases/TC-036-03.md) | AC3, AC4, AC5 | Admission versus attempt failure; bounded inputs/retries; zero partial publication; result epoch/count and error classification | 38 |
| [TC-036-04](../test-cases/TC-036-04.md) | AC3, AC4, AC5 | Exact trusted store/context; stale confirmation failure; privacy/pickle; absent/broken/skipped runtime rejection and installed smoke | 17 |

Counts are JUnit `per_tc` execution mappings in the
[repair provenance](REQ-036-review-fixes-provenance.json), not independent
acceptance counts. Groups may overlap and must not be summed as unique tests.

Review [reconciliation.py](../../../toolsets/iot/home-device-fabric/src/home_device_fabric/reconciliation.py)
and the explicit [state-store extension](../../../toolsets/iot/home-device-fabric/src/home_device_fabric/state_store.py)
alongside [regression tests](../../../toolsets/iot/home-device-fabric/tests/test_reconciliation.py),
[runtime gate probes](../../../toolsets/iot/home-device-fabric/tests/test_gate.py),
[installed smoke](../../../toolsets/iot/home-device-fabric/tests/reconciliation_artifact_smoke.py)
and [CI wiring](../../../.github/workflows/ci.yml).

Confirm that owner-provided capture closure, the exclusive per-home write
barrier, monotonic persisted epoch allocation, retry scheduling and post-capture
live-event drain remain explicit composition preconditions. The offline
coordinator does not implement or certify a live transport owner. Multi-entity
aggregation, dynamic registration and physical-device validation are outside
this increment.

## Source-specific verification

The [repair record](REQ-036-review-fixes.md) and provenance certify clean source
`07796cc325b22f761f200eefdcfb6b623921135a`: 1,960 fabric tests, zero failures,
errors or skips, all sixteen required-runtime flags, Ruff and strict mypy on
Linux aarch64 / CPython 3.12.12. Direct and sdist-derived package pairs each
passed isolated normal and optimized smokes, including 18 reconciliation
checks per run. [Mutation evidence](REQ-036-review-fixes-mutations.json)
records six killed mutations. The original
[implementation record](REQ-036-runtime-implementation.md) and
[initial provenance](REQ-036-artifact-provenance.json) remain historical.

[CI run 42558569174](https://github.com/rushwing/ai-family/actions/runs/42558569174)
verifies review baseline `98cb612347cb2450fb612aa7e36aff8820a86e4d`.
Rechecked on 2026-11-10: all fourteen executed jobs completed successfully,
including fabric, shared-contract and API matrices on Python 3.12/3.13/3.14,
their installed-artifact steps, governance, MCP and database integration.
Web and requirements jobs were skipped by path selection. This run certifies
that baseline, not subsequent documentation commits.

## Requested disposition

The independent reviewer should identify the exact reviewed commit, approve
or revise each TC criterion and mapping, assess AC1–AC5, and record findings,
checks actually executed and remaining environment limits. Lifecycle changes
must follow the registered roles and explicit human authority in the
[requirement standard](../../requirement-standard.md). The author must not
approve their own drafts. PR readiness, final human acceptance and merge remain
separate steps after review.
