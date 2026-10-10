# REQ-018 — Supplied Local Pre-review and Disposition

Date: 2026-10-09. Human-001 supplied a non-signing local pre-review of [draft PR #37](https://github.com/rushwing/ai-family/pull/37), head `c301f2293878723076f2e322bfe89a224f299b31`, against merged specification base `a87d235b5193f8b4ad5137c5018f9792895b0994`. The report explicitly supplies no independent T07/T10/T13 approval and made no tracked-file or GitHub changes. These results are attributed to the supplied reviewer, not author executions.

## Reported Verification

In a real Git worktree on Android/Termux aarch64, CPython 3.14.6 / pytest 9.1.1, the reviewer reports 1795 passed, zero failed/skipped with all six required-runtime flags: 302 Action cases (118/12/98/36/26/12 across TC-018-01–06) and 1493 existing cases. Governance/all 21 planning regressions, public-data/legacy/link/whitespace checks and an isolated installed-wheel smoke pass. Existing runtime modules are unchanged. Bare codeload trees initially produced Git-dependent environment failures; the real-worktree rerun is the report's authoritative result.

The report verifies missing Action runtime exits 4 in required Action mode, required Capability mode exits 1 on skipped Action cases, and optional mode exits 0 with explicit skips, using isolated copies. Adversarial probes cover trusted-context spoofing, ACK-only outcomes, type-exact idempotency, frozen-baseline/epoch eligibility, integer-position property validation, input/snapshot isolation, value-free diagnostics and 1–128 ASCII token bounds. No blocking finding is reported; AC8 remains for independent review. A further fresh-eyes review was still pending when this report was supplied; no result from it is inferred here.

Ruff/strict mypy could not run in the reviewer's Termux environment; the report relies on CI for those checks and Python 3.13. [Final-head CI run 37906701476](https://github.com/rushwing/ai-family/actions/runs/37906701476) at the reviewed head passes eight applicable jobs, including the Python 3.12/3.13/3.14 contract matrix; two unrelated jobs skip by path filtering. This author session also checked GitHub's PR head, draft state and those job conclusions on resumption.

## Informational Findings

- F-1: document that this revision cannot represent cancellation reasons. The package README now states cancelled requires null error; no envelope or behavior changes.
- F-2: retain the reviewed late eligibility check. Dispatch context may describe uncertain execution; confirmed success still requires an eligible current-epoch baseline. Adding an early epoch restriction would change the frozen contract and is unnecessary for this nonblocking finding.
- F-3: document the separate requester identity grammar. Subject/member IDs are nonblank strings of at most 256 characters retained exactly, allowing spaces and Unicode; contract correlation tokens retain their strict ASCII bounds. The README explains the externally established identity use case.
- F-4: retain accepted/running/terminal states. Dispatch and queue semantics remain outside this revision; any future queued state needs separate contract review.

## Review Boundary

These documentation clarifications do not change source/test artifact `c6e2ce5`, acceptance criteria, TC code or runtime behavior. Keep [REQ-018](../archive/done/features/REQ-018.md) req_impl_review / evaluator-001, review_round 0, AC1–AC8 unchecked and TC-018-01–06 implemented. Informational clarifications introduce no review return or req_bug. PR #37 stays draft pending human-arranged independent combined review or explicit human final disposition. No readiness, queue approval or merge is authorized by the supplied report.

## Author Follow-up Validation

After these documentation changes, `bash scripts/check.sh` passes all governance gates and 21 planning regressions. `python3 tools/check_home_intelligence_public_data.py`, `python3 tools/check_home_intelligence_requirements.py` and `git diff --check` pass. Runtime tests were not rerun for this documentation-only follow-up; the supplied reviewer results and original source/test verification retain their separate attribution above.
