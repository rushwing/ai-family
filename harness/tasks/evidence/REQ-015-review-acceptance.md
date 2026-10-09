# REQ-015 — Merge and Done Closeout

Date: 2026-10-09. Authority: human-001 explicitly accepted AC1–AC7 and TC-015-01–06 under the PR #31 merge disposition, then requested recording the merge, done archival and current-state/link updates. This is the human final disposition, not an independently signed evaluator review.

## Merge Provenance

GitHub confirms [PR #31](https://github.com/rushwing/ai-family/pull/31) is MERGED at `2026-10-09T03:16:42Z`. Final head: `832bc9f660e0fb415534d6049317acf348df41c7`; merge: `58f411edf7199ede236f274632b77b73d08bed02`. Local main and origin/main match that merge. Historical implementation, CI, author checks and human-supplied non-signing DSH results remain attributed in [runtime evidence](REQ-015-runtime-implementation.md).

## Post-merge Offline Verification

Tested source commit: `58f411edf7199ede236f274632b77b73d08bed02`, before documentation-only closeout/admission edits. Linux aarch64, non-root UID 1000, CPython 3.12.12, pytest 9.1.1; editable package in `/tmp/req014-env`. No HA credentials, provider service or hardware.

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime -q \
  --junitxml=/tmp/req015-closeout-results.xml
```

957 passed, zero skipped/failed. JUnit: `/tmp/req015-closeout-results.xml`.

| Scope | Passed | Skipped | Failed |
|---|---:|---:|---:|
| TC-015-01 | 137 | 0 | 0 |
| TC-015-02 | 17 | 0 | 0 |
| TC-015-03 | 19 | 0 | 0 |
| TC-015-04 | 23 | 0 | 0 |
| TC-015-05 | 37 | 0 | 0 |
| TC-015-06 | 5 | 0 | 0 |
| Inventory/binding and guard infrastructure | 719 | 0 | 0 |

## Harness Disposition

Record T15 under human-001's explicit final instruction. AC1–AC7 stay accepted and all six TCs stay passing. No pending or linked unresolved req_bug prevents done. [REQ-015](../archive/done/features/REQ-015.md) becomes done / human-001 and is the sole archived specification. Pending-review statements in historical handoffs are superseded; no T07/T10/T13 evaluator signature is invented. ACK-only task acceptance remains separate from physical convergence.

Repair Story, TC, evidence and shared-package links in the same closeout package. HI-S011 is admitted separately to REQ-016 for specification review only; its admission does not claim delivered Capability runtime.

## Closeout and Admission Validation

After archival and HI-S011 → REQ-016 admission, `bash scripts/check.sh` passes all governance gates and 21 planning regressions. Public-data and legacy requirements checkers, targeted local-link checks and `git diff --check` pass. The isolated planning fixture includes REQ-016 and the linked closeout evidence, and resolves archived REQ-015 while preserving lifecycle mutation tests. No runtime source or runtime acceptance-test code changes in this package.
