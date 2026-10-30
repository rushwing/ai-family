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
wheel checks, with explicit assertions surviving -O. Exact validation results
will be recorded after completion; no live HA or hardware result is claimed.
