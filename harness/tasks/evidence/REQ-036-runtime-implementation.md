# REQ-036 implementation handoff

On 2026-10-30 human-001 instructed “merge the pr andstart to implement”.
Specification PR #73 merged at e421635. The new implementation is generator
work under that instruction, not an independent T03/T07/T10/T13 signature.
REQ-036 remains req_impl with all acceptance criteria unchecked. Independent
TC-036 design and review remain pending; test_case_ref remains empty.

The implementation adds CurrentStateStore.reconcile_home and mark_home_stale,
plus an offline ReconnectReconciler. Reconciliation validates the complete
home before publication, preserves current desired intent under the store lock,
replaces reports/availability, merges eligible buffered observations, advances
the epoch, increments each device revision once and clears explicit stale in
one publication. Failed attempts report fixed diagnostics and only claim stale
after successful invalidation. The stale marker overrides TTL/uninitialized
freshness and persists through ordinary writes.

The composition owner must capture events and hold the home write barrier
across acquisition, retries, publication and post-closure drain; it allocates
and persists epochs and schedules retries using existing HA configuration.
Those owner responsibilities are preconditions, not an implicit scheduler or
transport integration delivered here. Discovery and mapper outputs are trusted
owner inputs; the coordinator cannot prove that a typed mapping was generated
from the supplied discovery snapshot. Only single-entity device bindings are
supported. No new lifecycle, network, device writes, HTTP/UI or durable state
store is introduced.

Captured events are detached dictionaries with normalized_delta as canonical
DeviceState JSON, original_ordering as canonical Ordering JSON, source_entity_id,
observed_at and a strictly increasing positive capture_ordinal. current_states
is a complete typed StateCollection. Source IDs remain inside the trusted
boundary. Matching events are deduplicated and compared with their entity's
snapshot last_updated as UTC instants before re-basing. buffered_event_count
on success counts eligible published events; on failure it is bounded by
capacity and describes captured input count. Successful publication returns
the pinned epoch; the owner starts its next live sequence at count + 1.

Generator verification lives in tests/test_reconciliation.py, relative to the
fabric package. It does not replace independently reviewed TC acceptance text.
The CI runtime-required flag rejects missing/broken reconciliation methods and
skips; installed package smoke is wired into both direct and sdist-derived
wheel checks, with explicit assertions surviving -O. No live HA or hardware result is claimed.

## Source-specific verification

Clean implementation source `449aa3377be761ab653e175660b8a4b2211b6b3d` (full ID in the provenance below), Linux
aarch64 / CPython 3.12.12. The full fabric suite ran with all sixteen CI
runtime-required flags: **1,938 passed, zero failures/errors/skips**, including
42 new generator regression cases and 132 gate cases. Ruff passed the complete
fabric package/tests; strict mypy passed all 20 runtime modules. Governance and
planning checks passed. The initial socket-restricted sandbox run failed in
23 existing loopback/timing cases; the final authorized run passed all cases
without changing runtime source or disabling tests.

[Artifact provenance](REQ-036-artifact-provenance.json) binds the full commit,
JUnit SHA-256 and exact case count, runtime hashes, direct/sdist-derived wheel
hashes and official dependency digests. Fresh offline installs of both wheel
pairs passed every smoke family. Reconciliation ran four times (two pairs,
normal and optimized isolated Python), with **13 explicit checks** each.
The CI acceptance count is updated to 1,938 and the six required-gate probes
cover missing/broken modules, missing methods, missing store methods, skips
and the successful path. The CI wiring mutation checks include the new flag.

[Draft PR #74](https://github.com/rushwing/ai-family/pull/74) is the implementation
review artifact. Subsequent evidence/PR-number edits do not change tested
runtime or test bytes. Final remote CI on Python 3.12/3.13/3.14 is separate
validation; local results certify Python 3.12 only. TC design/review, independent
implementation approval, implementation merge and Feature/Stage acceptance
remain pending.

## Remote CI verification

[GitHub Actions run 41042122098](https://github.com/rushwing/ai-family/actions/runs/41042122098)
completed successfully for PR head
`0a7b8a20664cd316f49468cdb3cf2e5d1eb8770b` on 2026-10-30. All fourteen
executed jobs passed, including the fabric, canonical schema and Home
Intelligence API matrices on Python 3.12, 3.13 and 3.14, governance gates,
REQ-002 integration, goal agent and MCP toolsets. The web and requirements
jobs were skipped by workflow path selection; they are not claimed as executed.
The tested head contains the unchanged implementation and test bytes from
the source-specific local verification above. This records CI success only;
independent TC design/review and implementation approval remain pending.
