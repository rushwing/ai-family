# REQ-032 / HI-S014 final acceptance and merge

[human-001][2026-10-19] Instructed “Merge PR and do ledger and housekeeping in
anopther PR”. This final disposition accepts AC1–AC4 and TC-032-01–04 combined
text/code/runtime delivery, including the collection-gate correction and O1–O3
fixes. It supersedes historical req_impl, unchecked-AC, implemented-TC, draft
and external-review stops. The supplied local pre-review remains non-signing;
no independent evaluator or T03/T07/T10/T13 signature is invented.

## Exact merge and verification

[PR #65](https://github.com/rushwing/ai-family/pull/65) was marked ready and
squash-merged with exact-head matching from
`7d1c86bab334a56cc9a4603709d4ea34f8b36cf6` as
`3e04d6e7044d46060df9a0a511ba93ff996eb4c9` at 2026-10-19T08:14:47Z.
GitHub merged state was read back. Local main was fast-forwarded to the squash
before creating `chore/req-032-acceptance-housekeeping`.

[Final-head CI](https://github.com/rushwing/ai-family/actions/runs/39218808199)
passed all eleven applicable jobs, including required fabric/shared suites and
fresh direct/sdist-derived installed packages on Python 3.12/3.13/3.14.
Two unrelated web/requirements jobs were path-filtered.

The [O1–O3 response](REQ-032-review-fixes.md),
[artifact provenance](REQ-032-review-fixes-artifact-provenance.json) and
[verification](REQ-032-review-fixes-verification.json) retain actual clean-source
execution on `47be5b909cd48f7dc3016fc0d8a768a9f90a2043`, Linux aarch64 /
CPython 3.12.12: **1552 fabric / 1795 shared passes**, zero failures/errors/skips,
**121 mapper cases**, overlapping TC groups **4 / 20 / 97 / 13**, **134 targeted
checks**, ten isolated runtime-gate probes and **eleven detected runtime mutations**.
Ruff, strict mypy (17 runtime sources), nine governance/requirements scripts and
21 planning regressions passed. Fresh direct/sdist-derived shared/fabric pairs
installed with eight officially verified dependency wheels; all installed
families passed. Four normal/optimized mapper smokes each passed **16 explicit
checks**, offline:true and rules_version:1. Final head adds evidence only beyond
that tested source; runtime/test bytes match.

The [original execution](REQ-032-runtime-implementation.md),
[artifact provenance](REQ-032-artifact-provenance.json) and
[verification](REQ-032-verification.json) remain historical evidence on clean
source `d3b941a93c32f2cc00f365c170be3d158528a47c`: 1515 fabric / 1795 shared
passes, 84 mapper cases, TC groups 4 / 17 / 63 / 13, eight detected runtime
mutations and four installed mapper smokes with thirteen checks each.
[Collection-gate verification](REQ-032-collection-fix-verification.json) records
amended test source `f66ab43879b39f033401516b31f02267c27190db` and another
1515-case fabric pass. Original shared/artifact executions were not retagged.
Earlier smoke-helper import-order and optional-runtime collection issues remain
recorded with their actual corrections. Historical results are not executions
of later amended bytes.

## Review dispositions and limits

O1 eagerly validates direct HAMappingResult construction: bounded strict JSON,
accepted inventory/binding contracts/references, exact count types/length/ranges
and matching output cardinalities. Valid replacement data cannot reinitialize
an existing result. O2 explicitly reserves grouped entities' entity assignments
without creating standalone Devices. O3 defines unresolved_areas per emitted
Device's unresolved nonnull reference, rather than distinct areas or entities.
New tests and installed checks cover these rules; three counter-validation
mutations join the original eight rerun against amended source.

The supplied non-signing local report separately attributes 1515 fabric / 1795
shared passes, 84 mapper cases, eight author plus five reviewer mutations and
custom probes to Android/Termux aarch64 / CPython 3.14.6 at `38ca7c5f`.
These remain attributed results for that earlier head. They are not generator
execution, verification of later fixes or independent lifecycle approval.
No new local Termux/Windows, live/private HA, hardware or long-soak result is
inferred. Public result construction validates structure, not execution origin.

## Ledger disposition

T15: the sole [REQ-032](../archive/done/features/REQ-032.md) is archived as
done / human-001, review_round 0, pr_number 65, four checked ACs and four
passing TCs. Actual TC authorship remains generator-001. No pending or linked
unresolved req_bug blocks done.

This separate housekeeping PR repairs archive links, product delivery state,
package navigation and isolated planning fixtures. Historical evidence Markdown
changes only REQ navigation links. All historical provenance/verification JSON,
runtime source/tests, shared contracts, dependencies and CI remain identical to
merged main. No new local runtime execution is claimed by this ledger.

Caller-owned identity allocation/retention remains explicit. Automatic allocation
or persistence, capability inference, store publication, query/API services,
reconnect reconciliation, device actions, live HA certification, BUG-033 and
Feature/Stage completion retain separate gates. This merge-and-housekeeping
instruction admits no next implementation. The housekeeping PR description
records governance, planning, requirements/public-data, Markdown and whitespace
verification.
