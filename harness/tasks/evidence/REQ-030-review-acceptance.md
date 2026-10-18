# REQ-030 final acceptance and PR #61 merge

[human-001][2026-10-18] Instructed “Review Passed. Merge PR and start another
PR to do ledger and housekeeping”. This accepts the combined REQ-030 / HI-S017
delivery, review fixes A–D, AC1–AC4 and TC-030-01–04. The earlier supplied local
pre-review remains non-signing; no independent T03/T07/T10/T13 identity or
approval is invented. Final disposition follows the explicit human acceptance.

## Exact merge and verification

[PR #61](https://github.com/rushwing/ai-family/pull/61) was marked ready and
exact-head squash-merged from accepted head
`bea6e222f9c3f9bdf08ebda717b01a4b4362430f` as
`3f9fad312c1d0cddaa6b9332d70fa405b729c6e2` at 2026-10-18T02:53:03Z.
GitHub merged state was read back; local main was fast-forwarded to the squash
before creating `chore/req-030-acceptance-housekeeping`.

[Final-head CI](https://github.com/rushwing/ai-family/actions/runs/39090742507)
passed all 11 applicable jobs, including required fabric/shared tests and fresh
installed packages on Python 3.12/3.13/3.14; two unrelated jobs were path-filtered.
The [review-fix execution](REQ-030-review-fixes.md) and
[provenance](REQ-030-review-fixes-provenance.json) retain actual Linux aarch64 /
CPython 3.12.12 execution on clean source
`ca9745c404c8d619d31f3b31139fd4cf9c427405`: **1296 fabric / 1795 shared passes**,
zero failures/errors/skips, **167 application cases**, nine runtime-gate probes,
three timeout-diagnostic cases and overlapping TC groups **101 / 36 / 27 / 19**.
Ten runtime mutations and one gate-diagnostic mutation were detected. Ruff,
strict mypy (15 runtime sources), governance and 21 planning regressions passed.
Fresh direct and sdist-derived shared/fabric wheel pairs installed with eight
officially verified dependency wheels. All smoke families passed, including
eight event smoke executions under normal/optimized isolated Python, each with
**18 checks, offline:true**. Accepted final head bea6e22 adds evidence only.

The [original implementation](REQ-030-runtime-implementation.md) and
[provenance](REQ-030-artifact-provenance.json) remain historical evidence on
clean source `6c02c062e84daef9171128b49b3012cd7e0cb5e7`: 1290 fabric / 1795
shared passes, 164 application cases, TC groups 98 / 36 / 27 / 13, nine detected
runtime mutations and eight installed event smokes with eighteen checks each.
Historical source counts and provenance are not overwritten by later results.

## Review findings and verification limits

A raises the finite gate deadline from 30 to 90 seconds and retains command,
stdout and stderr on timeout; three deterministic byte/text/absent-output cases
execute. The initial Termux transient failure was not reproduced or conclusively
attributed. B explicitly documents that canonical JSON cannot prove observation
origin: callers admit verified observations and route ACKs separately. An
enforced origin marker requires a future shared-contract change. C maps final
merge-result parse failures to private, fixed-path invalid_event before atomic
publication; three injected malformed-result cases execute. D documents the
linear scan of registered rows plus this home's member orders under the lock.

The user-supplied non-signing pre-review separately reports 1290 fabric / 1795
shared passes, 164 application cases, ten groups of custom probes and nine
detected mutations on Android/Termux aarch64 / CPython 3.14.6 at eebfda58.
It reports one initial transient gate failure followed by clean reruns and
stress probes, direct installed-smoke agreement, and inability to run fresh
venv wheel pairs locally. These are attributed reviewer results for that earlier
head; they are not new generator execution or verification of later fixes.
No new local Termux/Windows, real HA, hardware or long-soak result is inferred.

## Ledger disposition

T15: the sole [REQ-030](../archive/done/features/REQ-030.md) is archived as
done / human-001, review_round 0, pr_number 61, four checked ACs and four
passing TCs. TC owners remain generator-001 to preserve authorship. No pending
or linked unresolved req_bug blocks final disposition. Historical req_impl/draft
review stops are superseded by this explicit final human disposition.

This separate housekeeping PR updates incoming archive links, current product
state, package navigation and isolated planning fixtures. Historical evidence
Markdown changes only its REQ navigation links; all historical evidence JSON,
runtime source/tests, shared contracts, dependencies and CI baseline remain
byte-identical to merged main. No new runtime execution is claimed by this ledger.

Registry mapping, query/API services, authentication integration, durable epochs
and state, reconnect reconciliation, live HA/device actions, BUG-033 and
Feature/Stage completion retain separate gates. No next implementation is
admitted by this merge-and-housekeeping instruction.

## Housekeeping verification

The housekeeping PR description records its governance, 21 planning regression,
public-data/requirements, Markdown link and whitespace checks. Runtime results
remain tied to the accepted sources and final-head CI above.
