# REQ-038 local pre-review dispositions

Human-001 requested fixes for O1–O5 after a local pre-review of PR #78 head
`9e0ae41913bd9a661dc44009ce4f039d897a47b1`. That report explicitly supplies
neither an independent review signature nor approval. This follow-up is
generator work under the existing `req_impl / generator-001` authorization.

| Observation | Disposition |
| --- | --- |
| O1: missing internal entry could raise `StopIteration` | Fixed. Entry lookup has a default; a missing entry returns `unsupported_operation` with null request/operation. A fault-injection regression retains other entries, checks no fallback, preserves semantic and missing-binding precedence, and counts zero ambient/provider effects. |
| O2: publicly constructible internal result record | Retained as permitted by the REQ and REQ-037 convention. The class now explicitly documents that direct construction performs no validation; trusted callers obtain checked plans through `ActionResolver.resolve`. Neither a result type nor a resolved plan grants dispatch authority. |
| O3: fixed REQ-033 v1 mapping shapes | Retained as required by the exact-mapping contract. The helper now documents its v1 boundary and preceding exact packaged-descriptor check. Real mapper/inference composition remains covered by source and installed smoke tests. |
| O4: independent TC/implementation review pending | Still pending external evaluator action. The review handoff now lists each TC review and the AC1–AC4 implementation assessment required at an exact reviewed head. No independent signature, TC approval, acceptance or lifecycle transition is claimed. |
| O5: direct access to validated HA binding fields | Retained. An inline comment records the construction-time `BindingCollection` validation on which this access depends. No duplicate binding validator or accepted-schema change is introduced. |

The [REQ](../features/REQ-038.md) and proposed
[TC-038-02](../test-cases/TC-038-02.md) now describe the defensive mismatch case.
The regression deliberately bypasses the frozen snapshot solely for fault
injection; public construction still guarantees matching validator/entry data.
CI's expected full-suite count increases from 2,162 to 2,163.

## Verification

The revised resolver's targeted suite passes **98 cases**. Ruff passes the
full fabric package/tests; strict mypy passes all **22 runtime modules**.
Seven isolated full-package mutations are killed, including removing the new
missing-entry guard (**1 failed / 97 passed**). The six existing semantic faults
remain detected. The original tracked runtime is unchanged by mutation runs.

The full fabric suite passed **2,163 cases in 91.72 seconds**, with all eighteen
required-runtime flags and zero failures/errors/skips. Existing wire-transport
regressions ran outside the sandbox with authorized loopback socket access;
the sandboxed attempt was interrupted and is not claimed as passing.
All governance gates and **21 planning regressions** passed. Changed Markdown
links and whitespace passed checks. Accepted fabric modules and shared schemas
remain byte-identical to merged main.

Revised-source SHA-256 values:

- Runtime: `5c829d6901b69d84e91ba3ab439a1d5953eebbbbade93db51deebaa92968f48a`.
- Source tests: `dcd3adfc3013fc88233e87848f70366152aaa60a5d0524e36ea64b1af1c731f5`.
- Full-suite JUnit: `3ed28524b897be52e9ec6c39343647ecea96cfc4da0acd03456285e2eb46d81d`.

Updated-head CI additionally runs the Python 3.12/3.13/3.14 matrices, fresh
direct/sdist-derived wheel builds and normal/optimized installed smokes.
Its results belong to the tested PR head, separately from the baseline evidence.

## Evidence identity and review boundary

The original [provenance](REQ-038-artifact-provenance.json),
[mutation report](REQ-038-mutations.json) and
[implementation delivery](REQ-038-runtime-implementation.md) remain historical
evidence for clean implementation source `545be969`. They are not relabeled as
verification of this revised runtime. Updated CI must be attributed to its own
tested head, including fresh wheel-pair builds and installed smokes.

[External combined review handoff](REQ-038-review-handoff.md) remains the next
step. REQ-038 stays `req_impl / generator-001`, all four TCs stay draft,
AC1–AC4 stay unchecked and PR #78 stays draft.
