# REQ-036 / HI-S007 final acceptance and merge

[human-001][2026-11-10] Instructed “no more findings. merge pr and do leger
and house keeping in another pr”. This final disposition accepts AC1–AC5 and
the combined TC-036-01–04 text/code/runtime delivery, including T1/F1–F6
repairs and second-round copy/deepcopy coverage. It supersedes prior req_impl
stopping boundaries, unchecked ACs, draft TCs, draft PR and pending final
acceptance. The supplied local pre-reviews remain non-signing; no independent
evaluator identity or T03/T07/T10/T13 signature is invented.

## Exact merge and verification

[PR #74](https://github.com/rushwing/ai-family/pull/74) was marked ready and
squash-merged with exact-head matching from
[`e9d98d637411abb678645c9fbbbdbe5db18607f9`](https://github.com/rushwing/ai-family/commit/e9d98d637411abb678645c9fbbbdbe5db18607f9)
as [`a64e539220f9119e26de679cc52b66ec9e97bde0`](https://github.com/rushwing/ai-family/commit/a64e539220f9119e26de679cc52b66ec9e97bde0)
at 2026-11-10T04:38:17Z. GitHub merged state, merge SHA and timestamp were
read back. The separate `chore/req036-acceptance-housekeeping` branch starts
from that merged main.

[Final-head CI run 42755692987](https://github.com/rushwing/ai-family/actions/runs/42755692987)
completed successfully: **fourteen successful jobs, two path-filter skips**.
Fabric, shared-schema and API matrices passed on Python 3.12/3.13/3.14,
including direct/sdist-derived installed-artifact checks. Governance, MCP,
GoalAgent and database integration passed. Web and requirements jobs were
unrelated path-filter skips, not skipped acceptance cases.

[Second-round verification](REQ-036-second-round-verification.json) records
Linux aarch64 / CPython 3.12.12 execution: **1,960 fabric tests**, zero
failures/errors/skips with all sixteen required-runtime flags, 64 targeted
reconciliation cases, TC mappings **11/6/38/17**, Ruff, strict mypy on twenty
runtime modules and governance including 21 planning regressions. TC groups
can overlap and must not be summed as unique cases. Its manifest explicitly
records dirty base `3826e87a` and exact tested runtime/test/TC hashes; it is
not relabeled as a clean-commit artifact attestation. Final-head CI certifies
the committed follow-up separately.

[Repair artifact provenance](REQ-036-review-fixes-provenance.json) certifies
clean source `07796cc3`, with 1,960 cases and four reconciliation installed
smokes of **18 checks** each: direct/derived pairs, normal/optimized Python.
Runtime bytes are unchanged in the final implementation; follow-up tests add
copy/deepcopy assertions. [Six killed mutations](REQ-036-review-fixes-mutations.json)
remain attributed to their recorded runtime/test bytes. Initial
[provenance](REQ-036-artifact-provenance.json) certifies `449aa337` and the
earlier 1,938-case/four 13-check source. These historical manifests remain
unchanged and are not substituted for final-head CI or new test bytes.

## Findings and attribution

T1 supplies four TC proposals and named execution mappings. F1/F2 define
success versus failure epoch/count semantics. F3 enforces exact store type;
F4 rejects result pickle while preserving detached JSON; F5 specifies complete
single-profile report replacement and missing/unavailable retention; F6 makes
deterministic store validation errors terminal. The second-round follow-up
explicitly verifies copy/deepcopy rejection for success and failure results.
See [first repairs](REQ-036-review-fixes.md),
[second repairs](REQ-036-second-round-fixes.md) and the historical
[review handoff](REQ-036-review-handoff.md).

The human-supplied Termux/CPython 3.14.6 pre-review reports its own runtime
probes and seven killed mutations; it did not run Ruff/mypy or certify Windows.
Its initially stale editable import was corrected by the reviewer before the
reported second-round pass. These are reviewer-attributed observations, not
generator executions or independent approval. Final acceptance comes from
the explicit human merge instruction.

## Ledger disposition and housekeeping scope

T15: the sole [REQ-036](../archive/done/features/REQ-036.md) is archived as
done / human-001, review_round 0, pr_number 74, five checked ACs and four
passing TCs. Actual TC authorship remains generator-001. No pending or linked
unresolved req_bug blocks done. The housekeeping PR repairs archive links,
planning fixtures and delivery descriptions. Historical evidence Markdown
changes only navigation or adds a superseding closeout link; historical JSON,
runtime/tests, dependencies and CI remain identical to merged main, except
the isolated planning fixture needed for archive navigation.

This ledger claims no new runtime execution. Governance/planning, public-data,
legacy requirements, links and whitespace are verified for housekeeping;
any CI execution is attributed to its own head.

The offline coordinator requires owner-managed capture/write barriers,
persisted monotonic epochs, retry scheduling and post-capture live drain.
Live HA/device certification, multi-entity aggregation, dynamic inventory,
durable state, device writes, deployment, BUG-033 and Feature/Stage acceptance
retain separate gates. This instruction admits no next implementation. The
housekeeping PR remains unmerged for review.
