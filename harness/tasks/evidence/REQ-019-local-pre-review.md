# PR #39 non-signing local pre-review dispositions

Human-supplied report targets `d03567ba7f1f817d76c961979b677b8dd7bc2655`
on Android/Termux aarch64, CPython 3.14.6, pytest 9.1.1. It reports no blocking
findings and reproduces the 108 provider/1,795 shared cases, direct/derived
installed-wheel smoke, and CI. Ruff/mypy are corroborated by CI, not run locally
in Termux. The supplied fresh-eyes/mutation results are attributed to that report;
its local scripts and worktree were not available in this workspace.

Generator-001 responds within the previously authorized combined delivery scope.
These are test/documentation amendments for external review, with no runtime
change or independent T03/T07/T10/T13 approval. REQ remains
`req_impl_review / evaluator-001`, review_round 0; ACs remain unchecked, TCs
implemented, and PR #39 draft.

| Finding | Disposition |
|---|---|
| S-1 | All determinism/log-isolation comparisons use sorted strict JSON text, distinguishing bool/int/float. |
| S-2 | TC-019-06 asserts provider/Action token regex patterns and flags match. |
| F-1 | Proposed API/REQ clarification preserves existing lexicographic task_id order for simultaneous deadlines. TC-019-04 submits task-b before task-a and asserts task-a times out first; all deadlines precede same-time script deliveries. External review must approve this clarification. |
| S-3 | API documents provider depth 24 inclusive, root at 0, with delegated depth-16 bounds preserved. TC-019-01 exercises depths 24 and 25 through configuration admission. |
| F-2 / S-6 | REQ/API document independent epoch 1 and its inability to lower an accepted epoch≥2 snapshot. TC-019-02 uses real Task helpers to admit an epoch-2 Task and verifies both inputs are delivered/logged while only the epoch-2 report remains current. Independent inputs can update eligible epoch-1 snapshots. |
| F-3 | API states snapshot reads may share frozen records with immutable nested storage; mutable JSON serialization remains detached. |
| F-4 | All six TC frontmatter owners identify evaluator-001 as text designer; attribution separately names generator-001 as automated-code author. Neither attribution implies independent approval. |
| F-5 / S-7 | API distinguishes caller-adjudicated settlement from simulator-generated timeout. TC-019-04 verifies snapshot/discovery and advance(0) emit no timeout; advancing through the deadline emits it. No new elapsed-time eligibility rule is imposed on settle, which may reflect external caller adjudication. |
| S-5 | README/API require compatible paired distribution or a configured private index; fabric's declared dependency is retained. No package publication is claimed or performed. |
| S-4 | Early iterator close semantics already documented and tested; retained. |

Follow-up local verification and artifact provenance are recorded in
[runtime evidence](REQ-019-runtime-implementation.md). The original report remains
non-signing evidence; no bot-review signature, queue approval, readiness or merge
is inferred.
