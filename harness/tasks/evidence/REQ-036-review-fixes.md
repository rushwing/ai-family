# REQ-036 local pre-review fixes

Human-001 supplied a local pre-review of PR #74 at 219ae6a8 and instructed
“fix all findings”. This extends the generator implementation work while
preserving req_impl / generator-001, unchecked ACs and draft PR status.
The report explicitly disclaims independent T03/T07/T10/T13 approval.

| Finding | Generator action | Review boundary |
| --- | --- | --- |
| T1 | Added four TC-036 draft documents, REQ links, named test mappings and tc036 markers including runtime gates/installed smoke. JUnit records tc_groups and artifact provenance records per_tc. | Missing artifacts/mapping addressed; independent TC design/review and implementation acceptance remain pending. Drafts are generator proposals under the explicit fix instruction, not independent signatures. |
| F1 | Documented and tested epoch: pinned only on success; validated requested epoch on failure, otherwise None. A failed request epoch does not advance the store or live path. | Compatible clarification. |
| F2 | Documented and tested success count as eligible published events; failure count as captured input capped at capacity, zero before admission/list validation. | Overflow count is deliberately capped, not exact input size. |
| F3 | Require exact CurrentStateStore before accessing methods. Reject duck types, subclasses and unrelated objects with fixed construction error. | Fault injection now patches methods on the real class. |
| F4 | Reject result pickle with a fixed error; keep detached to_dict/JSON export. | Tested success/failure and legacy/current pickle protocols, plus optimized installed smoke. |
| F5 | Explicitly specify whole-report replacement for known/unknown single-profile observations. Test extra prior-member removal and missing/unavailable retention. | Single-entity scope remains unchanged. |
| F6 | Classify deterministic store input/contract validation errors as terminal invalid_input; epoch conflict stays terminal; unexpected failures stay retryable store_failure. | Fixed diagnostics and stale confirmation preserved. |

## Verification

Verified clean source `07796cc325b22f761f200eefdcfb6b623921135a` on
2026-11-09, Linux aarch64 / CPython 3.12.12. The full fabric suite passed
**1,960 tests, zero failures/errors/skips**, with all sixteen required-runtime
flags. Ruff passed the full fabric package and strict mypy passed all twenty
runtime modules. Governance, planning/local links and CI wiring checks passed.

[Updated artifact provenance](REQ-036-review-fixes-provenance.json) records
`source_dirty: false`, the source commit, JUnit digest, runtime hashes,
direct/sdist-derived wheel hashes and official dependency digests. Fresh offline
installs of both package pairs passed every smoke family. Reconciliation passed
18 explicit checks in each of four runs (direct/derived, normal/optimized).
JUnit per-TC mappings are recorded, including all four tc036 groups; these are
generator execution mappings and do not approve the draft TC criteria.

[Mutation evidence](REQ-036-review-fixes-mutations.json) records six killed
mutations. Its runtime and test hashes match this committed source. Initial
provenance in REQ-036-artifact-provenance.json remains historical and unchanged;
it certifies 449aa337, not these fixes.

The first artifact build was blocked while downloading dependencies in the
network-restricted sandbox. The authorized fresh build completed outside that
sandbox; no verification checks were disabled. Local results certify Python
3.12; remote CI validation is recorded separately after completion.

## Remaining approval work

External reviewers must review or revise the four draft TC criteria and their
implementation mappings, then perform implementation acceptance. No TC draft
is promoted to reviewed/passing merely because generator probes execute.
No independent evaluator identity, lifecycle transition, merge, physical-device
result or Feature/Stage acceptance is asserted.
