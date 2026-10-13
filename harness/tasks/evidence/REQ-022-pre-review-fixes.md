# REQ-022 — PR #46 Pre-review Finding Disposition

[generator-001][2026-10-13] Changes under human-001's “Fix all findings” instruction. Both supplied reports concern head 38a7a20afd6155d03fcf13c01f283bb609a7ff35 and explicitly disclaim independent T07/T10/T13 approval. Reviewer execution claims below are attributed to those reports; they are not new author executions or independent signatures.

## Disposition

F-1: README and API explain that preserved explicit port spelling gives equivalent endpoints different stored strings (e.g. :443/:00443). Endpoint equivalence/deduplication is outside this API; future transport must define a reviewed policy. Preserve the frozen Q1 behavior.

F-2 / information-B: README now puts the diagnostic/transport distinction directly after the example: use redacted snapshots/JSON for diagnostics; base_url and access_token_for_transport() expose the normalized endpoint and original token for trusted composition and must not be logged. API carries the same instruction. The existing private-slot/debugger/memory exclusions remain explicit; name mangling is not a security guarantee.

F-3: Retain every raw serialization refusal on configuration and credential wrapper, including __getstate__, __reduce__ and __reduce_ex__. The reports found these effective; removing one overlapping hook is not a requested functional correction. API documents this overlap.

F-4: README/API describe key-scan order and fixed validation precedence. Source uses any(...) for unknown keys; every match yields the same unknown_field/settings.<unknown> error. It does not expose which key matched. Thus input insertion order cannot change the visible unknown-key diagnostic, contrary to a possible reading of “order-dependent”; no order-dependent error contract is introduced. Non-string key rejection precedes unknown keys; required/numeric checks use declared order.

F-5 / information-C: Record receipt of the two technical pre-review reports and this generator follow-up in REQ-022. No named independent evaluator or formal handoff was supplied. Preserve the human's explicit req_impl stop. A later human assignment must record the actual evaluator and authorized req_impl_review transition before formal evaluation; do not manufacture that actor or a T07/T10/T13 signature from these reports.

F-6: Repeated reviewer git fetch failures and fallback codeload tarball/git init are reviewer-environment provenance, not a repository defect. Record the reported fallback without changing user networking, git configuration or tracked runtime behavior. The reports identify the compared head/base and say the 20-file comparison agreed with GitHub.

Information-A / equivalent mutations: Add a source comment and API note that the ASCII scan and authority ?/# exclusions overlap host/port/root validation. Keep the explicit guards. A surviving equivalent mutation does not prove a functional coverage gap; the reports' sampled comparisons are not a proof over every possible input.

Information-D: Keep the existing installation prerequisite: compatible distributions must be installed into the pytest interpreter because -I ignores PYTHONPATH. Optional-mode skip is documented; the required flag rejects absence/skips. No environment cleanup or new installation flow is needed.

Information-E / validation limits: The reviewer reproduced one direct wheel pair on Termux CPython 3.14.6, using virtualenv because ensurepip is unavailable. Three-version direct/derived wheel hashes, Ruff and strict mypy were not independently reproduced there. Keep recorded author provenance and CI evidence distinct from reviewer execution; neither report establishes independent reproduction of the entire artifact matrix.

## Mutation Accounting

The report's aggregate “8 real / 4 equivalent / 13 mutations” is inconsistent with its displayed table. That table lists nine captured real mutations (M1, M2, M4, M5, M6, M7, M8, M9b, M11) and three equivalent mutations (M3, M10, M12), totaling twelve classified entries. It separately describes a discarded preliminary M9. A further ?/# exclusion mutation is mentioned outside the table without its own complete row. Retain the individual reported results, but do not certify the aggregate counts or invent missing executions. Original reviewer scripts/raw logs would be needed to reconcile a complete inventory. This discrepancy concerns report accounting, not a demonstrated runtime defect.

## Validation and Stop Boundary

This correction changes README/API/REQ/evidence text and Python comments only. The historical source/artifact matrix remains attributed to 64bc81d6aa3e2514ed115db0154d30143900dbae. No new wheel hashes or three-interpreter runs are implied.

Correction validation: CPython 3.12.12 passes all 462 fabric cases with all four required flags, zero failures/skips. Ruff passes; strict mypy reports no issues in all nine source files. Governance gates and 21 planning regressions, legacy requirements/public-data validation and git diff --check pass. Runtime AST matches reviewed head 38a7a20a; local Markdown targets resolve and REQ/AC/TC state checks preserve the stop boundary. The full historical shared/three-version/artifact matrix was not rerun for this comment/documentation correction. Final-head CI is checked separately after publication.

REQ remains req_impl / generator-001, eight ACs unchecked, six TCs implemented and PR #46 draft. Neither fix authorization nor technical pre-review authorizes ready/bot/queue/merge or independent acceptance.


## Second-round Confirmation and Final Disposition

Human supplied a second-round pre-review of 07d5f06b confirming the runtime AST identical to 38a7a20a, 462 fabric / 1,795 shared passes in the reviewer's installed Termux environment, and closure of all F-1–F-6/information items. The reviewer accepted the unknown-key diagnostic correction and explicitly corrected mutation accounting to nine captured real and three equivalent table entries. The reviewer's token-in-snapshot M4 (17 failures) differs from the adversarial report's token-in-repr M4 (one failure); retain attribution rather than merging those counts. These are supplied reviewer results, not new author executions.

Human then explicitly authorized PR #46 merge and separate housekeeping, superseding the historical stop boundary above. [Closeout evidence](REQ-022-review-acceptance.md) records the acceptance/merge; no evaluator assignment or independent approval is invented.
