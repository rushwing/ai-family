# REQ-037 implementation delivery

Human-001 authorized HI-S024 / REQ-037 combined specification, proposed TC,
runtime and verification work on 2026-11-10, stopping at req_impl for external
review. The sole [REQ](../features/REQ-037.md) remains req_impl / generator-001,
with AC1–AC4 unchecked and TC-037-01–04 draft. No independent approval or
merge is asserted.

ActionValidator performs pure semantic preflight against one fixed Inventory
and detached per-device descriptors. It reuses accepted ActionRequest and
CapabilityDescriptor validators. Validity grants no permission or dispatch.
Typed ordered rejections cover unknown scope/support, uninitialized metadata,
exact version mismatch, read-only descriptors, unknown action and invalid
arguments. Configuration, finite JSON/byte limits, redaction, immutability and
serialization behavior are explicit in the REQ. No accepted runtime module,
shared schema or descriptor is modified.

Counted ambient denial and provider-method spies cover accepted and rejected
calls. Required gate probes and installed normal/optimized direct/derived
smokes are wired into CI and artifact provenance. All TC criteria/mappings are
generator proposals pending external review. Live transport/auth/confirmation,
audit, task/idempotency execution, action resolution and writes are separate.


## Local source verification

On 2026-11-10, Linux aarch64 / CPython 3.12.12, the full fabric suite passed
**2,056 cases, zero failures/errors/skips**, with all seventeen runtime-required
flags (87.48 seconds). The new validator adds 88 source cases and eight runtime
and isolated-smoke gate probes. The existing CI wiring test also maps to
TC-037-04. JUnit TC mappings are {'tc037_01': 12, 'tc037_02': 34, 'tc037_03': 41, 'tc037_04': 10}; overlapping
markers are not independent approvals or unique-case totals.

Ruff passed the complete fabric package/tests; strict mypy passed twenty-one
runtime modules. Governance and all 21 planning regressions passed, as did
public-data, legacy requirements, local-link and whitespace checks. Existing
loopback HTTP/WebSocket regression cases required an authorized full-suite run
outside the socket-restricted sandbox; the validator itself has no network I/O.
The runtime imports from this checkout's installed editable source.

[Mutation evidence](REQ-037-mutations.json) records six killed faults against
exact runtime/test hashes: wrong revision fallback, read-only write acceptance,
input-schema bypass, unknown/uninitialized metadata conflation, byte-boundary
regression and missing home isolation. Mutations run in temporary full-package
copies with import-location verification; tracked runtime bytes were never
modified. These are generator checks, not independent review signatures.

Direct/sdist-derived artifact checks and head-specific remote CI are recorded
separately after completion. No live HA, credentials, device writes, Windows
or Feature/Stage certification is claimed.
