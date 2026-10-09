# REQ-017 — Merge and Done Closeout

Date: 2026-10-09. Authority: human-001 supplied the non-signing local/fresh-eyes reports, then explicitly requested merging PR #34 and archiving REQ-017. Human final disposition accepts AC1–AC7 and TC-017-01–06; no independent T07/T10/T13 signature is invented.

## Merge Provenance

GitHub confirms [PR #34](https://github.com/rushwing/ai-family/pull/34) merged at `2026-10-09T06:05:21Z`. Final head: `d0ea7e9b0bc2d9c173ad6b1aea1e458cb766e5dd`; squash merge: `0443b84a72f4b759a17800389046d64e01985e87`. Local main matched this merge before the closeout branch. [Final-head CI run 37891572256](https://github.com/rushwing/ai-family/actions/runs/37891572256) passes eight applicable jobs: governance-gates, changes, req002-integration, goal-agent, mcp-toolsets and state-schema-tc on Python 3.12/3.13/3.14. Two unrelated web/workbook jobs skip by path filtering; public-data/legacy and installed-wheel checks still execute in each contract job.

Original source/test artifact `c1901bf` and author versus supplied Termux verification retain their attribution in [runtime evidence](REQ-017-runtime-implementation.md). Final acceptance/consumer-boundary changes are documentation only. S-1 retains structural/identity validation with specification content fidelity checked by independently transcribed TCs and VCS/release review; F-1 documents the OSError/UnicodeError wrapper limit. Future integration must validate Capability values before State updates. These informational dispositions introduce no runtime change or review return.

## Post-merge Offline Verification

Tested source commit: `0443b84a72f4b759a17800389046d64e01985e87`, before documentation-only archive edits. Linux aarch64, non-root UID 1000, CPython 3.12.12 / pytest 9.1.1. Tests use the configured checkout source path; no provider credentials, live services, hardware or dispatch.

```bash
/tmp/req014-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime -q \
  --junitxml=/tmp/req017-closeout-results.xml
```

1493 passed, zero skipped/failed. JUnit: `/tmp/req017-closeout-results.xml`.

| Scope | Passed | Skipped | Failed |
|---|---:|---:|---:|
| TC-017-01 | 44 | 0 | 0 |
| TC-017-02 | 71 | 0 | 0 |
| TC-017-03 | 35 | 0 | 0 |
| TC-017-04 | 20 | 0 | 0 |
| TC-017-05 | 23 | 0 | 0 |
| TC-017-06 | 4 | 0 | 0 |
| Existing inventory/binding/State/Capability/guards | 1296 | 0 | 0 |

## Harness Disposition

Record T15 under human-001's explicit merge/archive instruction. [REQ-017](../archive/done/features/REQ-017.md) is done / human-001 with review_round 0, accepted AC1–AC7 and passing TC-017-01–06. No pending or linked unresolved req_bug prevents done. Historical pending-review statements are superseded without inventing evaluator signatures. This is the sole archived specification; Story/index remain navigation only and engineering state resolves from Harness.

Repair Story, TC, evidence and package links; update current-state and requirements navigation. The planning fixture resolves archived REQ-017 while retaining active copies for lifecycle mutation tests. HI-S012's schema prerequisite is delivered; later stories still need their other dependencies and explicit admission. Feature/Stage completion and provider execution are not inferred from contract delivery.

## Closeout Validation

After archival, `bash scripts/check.sh` passes all governance gates and 21 planning regressions. Public-data and legacy requirements checkers, targeted archived-REQ/TC/evidence/package local-link checks and `git diff --check` pass. Only navigation/evidence documentation and the planning fixture change; no runtime source or runtime acceptance-test code changes. The sole specification resolves as done / human-001, with accepted AC1–AC7 and six passing TCs.
