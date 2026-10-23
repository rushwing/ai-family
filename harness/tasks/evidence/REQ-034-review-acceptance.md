# REQ-034 / HI-S018 final acceptance and merge

[human-001][2026-10-23] Instructed “Merge PR and do ledger and housekeeping in
another PR”. This final disposition accepts AC1–AC4 and TC-034-01–04 combined
text/code/runtime delivery, including O1–O3 fixes. It supersedes historical
req_impl, unchecked-AC, implemented-TC, draft and external-review stops. The
supplied local pre-review remains non-signing; no independent evaluator or
T03/T07/T10/T13 signature is invented.

## Exact merge and verification

[PR #69](https://github.com/rushwing/ai-family/pull/69) was marked ready and
squash-merged with exact-head matching from
`347912d15e500a3765b421af534f95515d5d25dc` as
`98d6db9834399d294b925bbec1165505687d3b57` at 2026-10-23T06:43:02Z.
GitHub merged state was read back. Local main was fast-forwarded to the squash
before creating `chore/req-034-acceptance-housekeeping`.

[Final-head CI](https://github.com/rushwing/ai-family/actions/runs/39910846483)
passed all eleven applicable jobs, including fabric/shared suites and installed
direct/sdist-derived packages on Python 3.12/3.13/3.14. Two unrelated web and
legacy-workbook jobs were path-filtered.

[Follow-up verification](REQ-034-review-fixes.json) and
[artifact provenance](REQ-034-review-fixes-provenance.json) identify clean
source `ea75814dbae324d8cdae4baa91f17267ef065ef2`, Linux aarch64 / CPython
3.12.12: **1888 fabric passes**, zero failures/errors/skips, **185 query cases**,
and a passing mutation baseline with **13/13 mutants detected**. Eight dependency
wheels match official release SHA-256 values. Fresh direct/sdist-derived pairs
pass all smoke families; four normal/optimized query runs each pass **22 explicit
checks**. Ruff, strict mypy across nineteen runtime modules, governance and
21 planning regressions, public-data and legacy-requirements checks passed.
Final implementation-PR head adds evidence only to that tested source.

[Original evidence](REQ-034-runtime-implementation.md),
[verification](REQ-034-verification.json) and
[artifact provenance](REQ-034-artifact-provenance.json) remain historical on
clean source `702d407646134062c253c32e142c022bd0d71435`: 1872 fabric and 1795 shared
passes, zero failures/errors/skips, 169 query cases, eleven detected mutants and
four query smoke runs of 20 checks. These original counts/hashes are not retagged
as executions of the amended runtime.

## Dispositions and attribution

O1: public QueryResult construction validates the entire bounded plain-JSON
envelope and rejects invalid data with redacted invalid_configuration errors;
valid data remains detached and process-control exceptions propagate.
O2: store invalid_identifier maps consistently to invalid_selector, with a
forced-store-error test and semantic mutant for this defensive path.
O3: new runner reports use non-null returncode. Historical reports correctly
contain exit_code (baseline 0, eleven mutants 1); they contain no returncode:null
field and remain unchanged. [Follow-up notes](REQ-034-review-fixes.md) preserve
the initial fixture-path and smoke-count test failures and successful reruns.

The human-supplied local pre-review at prior head 2b973c21 reports Android/Termux
aarch64 / CPython 3.14.6 execution: 1872 fabric / 1795 shared passes, eleven author
mutants, five additional mutants detected and nine groups of probes. Those are
attributed observations, not generator execution of later bytes or independent
lifecycle approval. No new Termux/Windows, live/private HA, hardware or long-soak
certification is inferred.

## Ledger disposition

T15: the sole [REQ-034](../archive/done/features/REQ-034.md) is archived as
done / human-001, review_round 0, pr_number 69, four checked ACs and four passing
TCs. Actual TC authorship remains generator-001. No pending or linked unresolved
req_bug blocks done.

This separate housekeeping PR repairs archive links, product/package delivery
state and isolated planning fixtures. Historical evidence Markdown changes only
REQ navigation. Historical JSON, runtime source/tests, shared contracts,
dependencies and CI remain identical to merged main. No new local runtime
execution is claimed by this ledger. Governance, planning, public-data,
requirements, local Markdown links and whitespace are checked for this PR.

HTTP query/authentication APIs, reconnect reconciliation, dynamic inventory,
durable policy/audit, device writes, live HA/device validation, BUG-033 and
Feature/Stage completion retain separate gates. This instruction admits no next
implementation. The separate housekeeping PR remains unmerged for review.
