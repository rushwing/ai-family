# REQ-028 final acceptance and PR #57 merge

[human-001][2026-10-17] Instructed “merge PR and then do ledger and house
keeping in another PR”. This accepts the combined REQ-028 / HI-S006 delivery,
AC1–AC4 and TC-028-01–04, including O1–O3 review fixes and the documented O4
reviewer environment limit. The supplied local pre-review expressly does not
sign T03/T07/T10/T13. No independent evaluator approval or identity is invented.

## Exact merge and verification

[PR #57](https://github.com/rushwing/ai-family/pull/57) was marked ready under
the explicit merge instruction and squash-merged with exact-head matching on
`37a04897c77284e14bca91f4d1f2048e4fa6078b` as
`ed1f00215d2b7e5b33ddc866d955069f67c40009` at 2026-10-17T12:54:16Z.
GitHub merged state was read back; remote refs were refreshed and local main
fast-forwarded before creating chore/req-028-acceptance-housekeeping.

[Final-head CI](https://github.com/rushwing/ai-family/actions/runs/39033833764)
passed 11 applicable jobs, including required fabric/shared suites and installed
package checks across Python 3.12/3.13/3.14; two unrelated jobs were path-filtered.
[Fix-source CI](https://github.com/rushwing/ai-family/actions/runs/39033633987)
also passed all applicable jobs. The
[review-fix execution record](REQ-028-review-fixes.md) and
[provenance](REQ-028-review-fixes-provenance.json) retain Linux aarch64 / CPython
3.12.12 results against clean source `55b8270ea5053d171b6e19f043e3c0e42f18c2f1`:
978 required fabric and 1795 shared passes, zero failures/errors/skips; 98
normalization cases and overlapping TC marker counts 19 / 71 / 6 / 10; lint,
strict typing, governance and 21 planning tests; eight officially verified
dependency wheels and fresh direct/sdist-derived paired installs with four
normal/optimized normalization smokes, eight checks each. The final accepted
head adds evidence only.

O1 explicitly documents and tests object attributes for unknown/unavailable.
O2 explicitly retains signed numeric offsets through ±23:59 with UTC conversion
and rejection boundaries. O3 maps canonical validation failures to fixed,
context-suppressed invalid_observation diagnostics. Five targeted mutations are
detected by assertions without timeouts. One redundant hour-guard mutation
survives because datetime independently rejects 24-hour offsets; it is recorded
separately and never counted as a detection. The initial stale smoke-count
assertion failure is superseded by the completed clean-source required run.

The supplied non-signing local pre-review separately reports 966 fabric / 1795
shared passes on Android/Termux aarch64 / CPython 3.14.6 at the earlier 06dc896
head, ten detected mutations, direct normal/optimized smoke agreement and
source/CI/ledger checks. Those are attributed reviewer results for that head,
not new generator executions or verification of the later repair source. O4 is
the reviewer's Termux ensurepip limitation; fresh Linux installed checks and CI
are separate evidence. No Windows, Termux fresh-venv, private HA or physical
hardware validation is inferred.

## Ledger disposition

T15: the sole [REQ-028](../archive/done/features/REQ-028.md) is archived as
done / human-001, review_round 0, pr_number 57, four checked ACs and four passing
TCs. TC owners remain generator-001 to preserve authorship. No pending or linked
unresolved req_bug blocks final disposition. Incoming links, product navigation,
package documentation and isolated planning fixtures follow the archive.

This separate PR records the authorized acceptance ledger and housekeeping.
Runtime source/tests, CI baseline, dependencies and all historical evidence JSON
remain unchanged from merged main. Earlier req_impl/draft statements remain
historical; this final human disposition supersedes them. BUG-033, live HA,
source deduplication, durable epochs, state storage, reconciliation, device
writes and Feature/Stage completion retain separate gates. No next increment
is admitted by this instruction.

## Housekeeping verification

Local governance, planning regression, public-data/requirements and Markdown
link/whitespace checks are recorded in the housekeeping PR description. Accepted
runtime verification remains tied to its tested source and final-head CI above;
this ledger does not claim a new local runtime execution.
