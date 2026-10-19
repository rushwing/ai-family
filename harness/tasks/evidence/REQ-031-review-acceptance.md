# REQ-031 / HI-S013 final acceptance and merge

[human-001][2026-10-19] Instructed “Merge PR63, and do ledger and housekeeping
in another PR”. This final disposition accepts AC1–AC4 and TC-031-01–04 combined
text/code/runtime delivery including F1/F2 fixes. It supersedes historical
req_impl, draft and external-review stops. The earlier local pre-review remains
non-signing; no independent evaluator or T03/T07/T10/T13 signature is invented.

## Exact merge and verification

[PR #63](https://github.com/rushwing/ai-family/pull/63) was marked ready and
squash-merged with exact-head matching from
`5920e131cde3538c001ce3dc36f8f6251c83e1e8` as
`8479058ca54f885817fb29996c9ffcb84be5e793` at 2026-10-19T06:22:49Z.
GitHub merged state was read back. Local main was fast-forwarded to the squash
before creating `chore/req-031-acceptance-housekeeping`.

[Final-head CI](https://github.com/rushwing/ai-family/actions/runs/39206550707)
passed all eleven applicable jobs, including required fabric/shared suites and
fresh direct/sdist-derived installed wheel pairs on Python 3.12/3.13/3.14.
Two unrelated web/requirements jobs were path-filtered.

The [follow-up execution](REQ-031-review-fixes.md) and
[provenance](REQ-031-review-fixes-provenance.json) retain actual Linux aarch64 /
CPython 3.12.12 execution on source
`16d0fe49a8da017e35de89e9b97f1fe51323d6ce`: **1419 fabric / 1795 shared passes**,
zero skips, **113 discovery cases**, overlapping TC groups **20 / 73 / 31 / 12**,
five new passing cases and two detected targeted mutations. Ruff, strict mypy
(16 runtime sources), nine governance/requirements scripts and 21 planning
regressions passed. Initial sandboxed discovery passed 112 cases but could not
bind its loopback socket; the authorized full suite passed all 1419 cases.
The final head adds evidence to that tested source.

The [original execution](REQ-031-runtime-implementation.md) and
[artifact provenance](REQ-031-artifact-provenance.json) retain their original
source/counts: 1414 fabric / 1795 shared passes, 108 discovery cases, TC groups
20 / 69 / 30 / 12, ten runtime-gate probes, twelve detected runtime mutations
and four fresh installed discovery smokes with fifteen checks each. Earlier REST
deadline failures under overlapping mutation load remain recorded alongside the
subsequent clean-source passing rerun. These historical results are not retagged
as executions of amended bytes.

## Finding dispositions and limits

F1 adds four otherwise valid duplicate-key cases covering envelope IDs/success,
record IDs and nested state attributes. Removing unique-key rejection fails all
four by assertions. F2 documents the defensive closed guard and adds controlled
close-during-successful-cleanup coverage. Ignoring cleanup cancellation fails
the new case; removing the guard alone is not claimed as a detected mutation.
O1 concerns the reviewer's Termux dependency reset and requires no repository edit.
No independent matrix reproduction, new local Termux/Windows run, live HA,
private credentials, physical-device or long-soak certification is inferred.

## Ledger disposition

T15: the sole [REQ-031](../archive/done/features/REQ-031.md) is archived as
done / human-001, review_round 0, pr_number 63, four checked ACs and four
passing TCs. Actual TC authorship remains generator-001. No pending or linked
unresolved req_bug blocks done.

This separate housekeeping PR repairs archive links, product delivery state,
package navigation and isolated planning fixtures. Historical evidence Markdown
changes only REQ navigation links. Historical provenance JSON, runtime source,
runtime tests, shared contracts, dependencies and CI remain identical to merged
main. No new runtime execution is claimed by this ledger.

Canonical mapping, capability inference, query/API services, state-store
publication, reconnect reconciliation, live HA/device actions, BUG-033 and
Feature/Stage completion retain separate gates. This instruction admits no next
implementation. The housekeeping PR description records governance, planning
regressions, requirements/public-data, Markdown link and whitespace checks.
