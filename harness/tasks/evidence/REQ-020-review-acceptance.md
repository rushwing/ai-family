# REQ-020 — PR #40 Merge and Done Ledger

Date: 2026-10-13. Authority: human-001 stated “REviewed and no blocking issues. Please merge the PR”, then explicitly requested REQ archival and related Harness ledger work. The human final disposition accepts AC1–AC8 and TC-020-01–06 combined text/code/runtime delivery. Earlier local pre-review reports remain non-signing; no independent T03/T07/T10/T13, bot-review or queue approval is invented.

## Merge Provenance

GitHub confirms [PR #40](https://github.com/rushwing/ai-family/pull/40) merged at `2026-10-13T03:39:38Z`. Final head: `e8cff4fb1c262c0c3a7fa52695513085438406c0`; squash merge: `6262456853b0d03b0a5cc334279c60e879f24b85`. Local main matched this merge before the ledger edits. The final head changed seven Harness documents only from reviewed delivery `2704aa7a38f0c1fc82a29e98bd6a16bc3d9159da`. Merge used exact-head matching.

[Final-head CI run 38342642223](https://github.com/rushwing/ai-family/actions/runs/38342642223) passed 11 jobs, including all six fabric/shared Python 3.12/3.13/3.14 runtime jobs and installed-artifact checks. Two unrelated product jobs were path-filtered. Earlier validation retains its source attribution in the [runtime evidence](REQ-020-runtime-implementation.md), [pre-review fix evidence](REQ-020-pre-review-fixes.md), [initial artifacts](REQ-020-artifact-provenance.json) and [fix artifacts](REQ-020-fix-artifact-provenance.json).

## Post-merge Offline Verification

Tested source: `6262456853b0d03b0a5cc334279c60e879f24b85`, before ledger changes. Linux aarch64, CPython 3.12.12, existing `/tmp/req019-env` with compatible editable fabric/state-schema packages. No live provider or hardware.

```bash
/tmp/req019-env/bin/python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini \
  toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime -q \
  --junitxml=/tmp/req020-closeout-fabric.xml
/tmp/req019-env/bin/python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q \
  --junitxml=/tmp/req020-closeout-shared.xml
```

Fabric/demo: 177 passed in 15.12 seconds. Shared: 1,795 passed in 11.67 seconds. Both have zero failures/errors/skips. TC-020 marker counts remain 5 / 4 / 16 / 14 / 16 / 3 = 58; REQ-019 marker groups total 119, including eight isolated gate self-tests. Installed wheel-pair and mutation evidence is preserved from the accepted fix delivery; those builds were not rerun for this documentation-only ledger.

## Harness Disposition

T15 under human final acceptance and explicit archive authorization: [REQ-020](../archive/done/features/REQ-020.md) is done / human-001, review_round 0, pr_number 40, with eight accepted ACs and six passing TCs. pending_bugs is empty; no active unresolved req_bug links to REQ-020. TC owner remains the actual text designer generator-001 under the documented combined-delivery exception; human acceptance does not invent independent evaluator authorship.

Move the sole authoritative REQ into `harness/tasks/archive/done/features/`, repair its relative links and all TC/API/evidence/product navigation links, and remove the active copy. Update HI-S026 navigation and CURRENT_STATE/operating rules to reflect delivered offline mock devices and CLI. The index already carries only reciprocal identity/navigation (`harness_ref: REQ-020`), so retain it without copying a lifecycle status; engineering state resolves from the archive. Maintain the deliberate active regression-fixture copies and add the closeout evidence fixture.

Historical pending-review and stopping statements retain their original attribution and are superseded by the human final disposition. This ledger neither admits HI-S027 nor completes HI-F009/R1. Broader provider conformance, live adapters, production authorization/services and Feature/Stage acceptance retain their separate gates.

## Ledger Validation

Governance gates and all 21 planning regressions pass; legacy requirements/public-data and git diff --check pass. All 81 local Markdown targets in changed/new documents resolve. Planning derives HI-S026 → REQ-020 done / human-001 from the sole archived specification; the admitted index entry retains no duplicated lifecycle state. The planning fixture additionally includes the newly referenced fabric README and closeout evidence and retains its deliberate active-REQ simulation. Runtime source and fabric/shared acceptance-test behavior are unchanged by this ledger.
