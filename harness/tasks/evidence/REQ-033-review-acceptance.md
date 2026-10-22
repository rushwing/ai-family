# REQ-033 / HI-S015 final acceptance and merge

[human-001][2026-10-22] Instructed “Merge PR67 and do ledger and housekeeping in
another PR”. This final disposition accepts AC1–AC4 and TC-033-01–04 combined
text/code/runtime delivery, including F1 and O1/O2 follow-up. It supersedes
historical req_impl, unchecked-AC, implemented-TC, draft and external-review
stops. The supplied local pre-review remains non-signing; no independent
evaluator or T03/T07/T10/T13 signature is invented.

## Exact merge and verification

[PR #67](https://github.com/rushwing/ai-family/pull/67) was marked ready and
squash-merged with exact-head matching from
`813541df565dd233e00374db50c4d535ae685c73` as
`9cbe0159cd2d82af9c7c6101e651240b969f7984` at 2026-10-22T06:21:06Z.
GitHub merged state was read back. Local main was fast-forwarded to the squash
before creating `chore/req-033-acceptance-housekeeping`.

[Final-head CI](https://github.com/rushwing/ai-family/actions/runs/39731885958)
passed all eleven applicable jobs, including required fabric/shared suites and
fresh direct/sdist-derived installed packages on Python 3.12/3.13/3.14.
Two unrelated web/requirements jobs were path-filtered.

[Follow-up verification](REQ-033-review-fixes.json) records executed file hashes,
JUnit totals and mutation logs on Linux aarch64 / CPython 3.12.12: **1691 fabric
passes**, zero failures/errors/skips, 73.29 seconds, **127 inference cases** and
**13/13 detected runtime mutations**. Ruff, strict mypy across eighteen runtime
modules, governance and 21 planning regressions passed. The gate now expects
127 optional skips and CI requires exactly 1691 fabric cases. Execution began
before matching source commits; no clean-tree execution is claimed. The
recorded tested revision is `d9577d20bfbd096a33eb052f74d58cf15de9db50`;
final head adds evidence only. Runtime bytes remain identical to original
implementation source `3630316340de97cfabc8d180595824c263c0905b`.

The [original execution](REQ-033-runtime-implementation.md),
[artifact provenance](REQ-033-artifact-provenance.json) and
[verification](REQ-033-verification.json) remain historical evidence on that
original clean source: **1690 fabric / 1795 shared passes**, zero
failures/errors/skips, **126 inference cases**, overlapping TC groups
**13 / 62 / 51 / 13**, ten isolated gate cases, two normal/optimized smoke cases
and eleven detected runtime mutations. Fresh direct/sdist-derived shared/fabric
pairs installed using eight officially SHA-256-verified dependency wheels;
all installed smoke families passed. Four normal/optimized inference smokes each
passed **16 explicit checks**, offline:true, rules_version:1. Original mutation
execution preceded its source commit; the runtime/test hashes matched exactly.
Historical counts and provenance are not retagged as later executions.

## Review dispositions and limits

F1 pins the cover upper bound with `2147483652` (bit 4 set, above 2147483647),
retains the accepted maximum control and checks exact unsupported counts.
Removing the upper bound now fails the new test. O1 adopts the report's private
constructor alternative: `_CapabilityResult` is internal to `infer()`'s validated
projection/counts, absent from `__all__`, and direct construction is unsupported.
O2 uses the existing six catalogue action-key equality assertions; the new
unexpected-sensor-action mutation fails four of them. F2 is equivalent because
the entity regex uses explicit ASCII ranges; no change was needed.

The first follow-up full run had 1688 passes / 3 failures because the isolated
gate expected 126 optional skips after collection increased to 127. Correcting
that expectation produced the full 1691-pass rerun above. Original sandbox
loopback failures (23 failed / 1667 passed), corrected shared invocation,
planning fixture correction, dependency-download restriction and strengthened
ordered-output assertion remain recorded with their actual corrections.

The supplied non-signing local report attributes 1690 fabric / 1795 shared
passes, 126 inference cases, eleven author mutations, six reviewer mutations
(four detected, one equivalent, one upper-bound gap) and custom probes at
`9986689a` to Android/Termux aarch64 / CPython 3.14.6. These are attributed
results for that earlier head, not generator execution of amended bytes or
independent lifecycle approval. No new local Termux/Windows, live/private HA,
hardware or long-soak result is inferred.

## Ledger disposition

T15: the sole [REQ-033](../archive/done/features/REQ-033.md) is archived as
done / human-001, review_round 0, pr_number 67, four checked ACs and four passing
TCs. Actual TC authorship remains generator-001. No pending or linked unresolved
req_bug blocks done.

This separate housekeeping PR repairs archive links, product/package delivery
state and isolated planning fixtures. Historical evidence Markdown changes only
REQ navigation links. All historical provenance/verification JSON, runtime
source/tests, shared contracts, dependencies and CI remain identical to merged
main. No new local runtime execution is claimed by this ledger.

Grouped/measurement State integration, store publication, query/API services,
reconnect reconciliation, device writes, live HA/device certification, BUG-033
and Feature/Stage completion retain separate gates. This merge-and-housekeeping
instruction admits no next implementation. The housekeeping PR description
records governance, planning, requirements/public-data, Markdown and whitespace
verification. The separate housekeeping PR remains unmerged for review.
