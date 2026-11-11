# REQ-037 implementation delivery

Historical implementation/review record. The later human final disposition in
[final acceptance](REQ-037-review-acceptance.md) supersedes pending approval
and req_impl stopping statements below; source-specific evidence remains historical.

Human-001 authorized HI-S024 / REQ-037 combined specification, proposed TC,
runtime and verification work on 2026-11-10, stopping at req_impl for external
review. The sole [REQ](../archive/done/features/REQ-037.md) remains req_impl / generator-001,
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

No live HA, credentials, device writes, Windows or Feature/Stage certification
is claimed.

## Resumed delivery verification

On 2026-11-11, the resumed validator and required-gate suite passed **228 cases,
zero failures/errors/skips** in 62.52 seconds on Linux aarch64 / CPython 3.12.12.
Ruff, strict mypy (21 runtime modules), governance, all 21 planning regressions,
public-data, legacy requirements, RLS and whitespace checks passed again.
The runtime and validator-test SHA-256 values still match the six killed
mutations and prior full-suite evidence above; no runtime/test bytes changed.

[Artifact provenance](REQ-037-artifact-provenance.json) records clean committed
source `f293c9ffc134ef9b2117138dee77644f1f1457c9`, the prior full-suite JUnit
SHA-256 and exact 2,056-case result, runtime hashes, all six distribution hashes
and verified official dependency digests. Fresh offline installs of direct and
sdist-derived schema/fabric wheel pairs passed every smoke family under normal
and optimized isolated Python. Action validation ran four times with **22
explicit checks** each. An earlier clean-source attempt stopped on a dependency
metadata connection reset; the fresh retry completed without bypassing digest
verification. Artifact acquisition required authorized network access.

[Draft PR #76](https://github.com/rushwing/ai-family/pull/76) delivers combined
specification, proposed TC criteria, implementation and generator verification
for external review. REQ-037 stays `req_impl / generator-001`; AC1–AC4 remain
unchecked and TC-037-01–04 remain draft. No independent approval, readiness or
merge is asserted.

## Remote CI verification

[GitHub Actions run 42996063008](https://github.com/rushwing/ai-family/actions/runs/42996063008)
completed successfully on 2026-11-11 for implementation head
`f293c9ffc134ef9b2117138dee77644f1f1457c9`. All fourteen executed jobs passed,
including fabric, shared-contract and API matrices on Python 3.12, 3.13 and
3.14, their installed-artifact checks, governance, MCP, database integration
and the goal-agent job. Web and requirements jobs were skipped by path
selection. This certifies the implementation baseline; subsequent provenance,
PR-number and review-navigation edits change documentation only. CI success
does not approve the draft TC criteria or grant independent acceptance.
