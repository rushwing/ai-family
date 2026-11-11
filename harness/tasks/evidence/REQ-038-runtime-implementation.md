# REQ-038 implementation delivery

Historical implementation/review record. The later human final disposition in
[final acceptance](REQ-038-review-acceptance.md) supersedes pending approval,
draft states and req_impl stopping statements below; source-specific evidence
remains historical.

Historical implementation evidence for source `545be969`; see the later
[pre-review follow-up](REQ-038-pre-review-fixes.md) for the defensive lookup
revision and its verification. Counts and hashes here retain their original scope.

Human-001 authorized HI-S020 / REQ-038 combined specification, proposed TC
text/code, runtime and verification on 2026-11-11, stopping at req_impl for
external review. The sole [REQ](../archive/done/features/REQ-038.md) stays
`req_impl / generator-001`, AC1–AC4 unchecked, TC-038-01–04 draft, and
[PR #78](https://github.com/rushwing/ai-family/pull/78) draft. No independent
criteria approval, evaluator signature, readiness or acceptance is claimed.

## Delivered behavior

ActionResolver snapshots one canonical Inventory, BindingCollection, REQ-033
capability projection and selected HA instance. It revalidates raw requests
through REQ-037 before selecting the exact registered binding, packaged
version-1 descriptor and fixed private capability map. Switch true/false and
curtain integer position resolve to deterministic private operation descriptions.
Grouped entities never imply first-entity fallback; missing, conflicting,
cross-instance, cross-device or malicious maps fail closed. Canonical API,
workflow payloads and accepted runtime/schema modules remain unchanged.

Public summaries expose only status/failure_code; provider details require the
private detached for_adapter export. Results grant no dispatch authority and
preserve no shared mutable payload. Constructor/resolve/repr/serialization,
bounds and failure ordering are specified in the REQ. Construction explicitly
loads the packaged catalogue; resolve does no I/O or ambient/provider effects.
Future dispatch must recheck live bindings/availability and enforce trusted
identity/member policy, durable confirmation/audit and task/idempotency gates.

## Source verification

Linux aarch64 / CPython 3.12.12, 2026-11-11: the full fabric suite passed
**2,162 cases in 94.15 seconds, zero failures/errors/skips**, with all eighteen
required-runtime flags. The resolver adds **97 source cases**, seven required
runtime probes and two isolated smoke probes. The existing CI-wiring mutation
test also maps to TC-038-04. JUnit groups are **6/51/39/11** for TC-038-01–04;
markers overlap and are not unique-case totals or independent approvals.
Existing HTTP/WebSocket loopback regressions ran with authorized socket access;
the resolver has no networking implementation.

Ruff passed the full fabric package/tests and changed governance/test files.
Strict mypy passed all **22 runtime modules**. All governance gates, legacy
requirements, fabric CI wiring, public-data checks and **21 planning regressions**
passed. Local Markdown targets and whitespace were checked. Every accepted
fabric runtime module, shared schema and historical evidence JSON remains
byte-identical to merged main. Only the new resolver module extends runtime.

[Mutation evidence](REQ-038-mutations.json) records six killed faults:
switch direction inversion, skipped entity membership, skipped instance
isolation, relaxed map allowlist, relaxed descriptor/revision selection and
missing-binding diagnostic conflation. Each ran in a temporary full-package
copy with checked import path, both passing and failing cases and the original
tracked runtime unchanged. Final mutation evidence identifies clean committed
source and exact runtime/test hashes, rather than relabeling dirty-tree probes.

## Installed artifacts and provenance

[Provenance](REQ-038-artifact-provenance.json) binds clean committed source
`545be9691db56813208b317e8f2300ef5c5be5c0`, the 2,162-case JUnit SHA-256,
resolver/runtime/test hashes, six distributions and eight dependency wheels
verified against official release digests. No dependency declaration changed.
Direct and sdist-derived schema/fabric wheel pairs were installed offline into
fresh environments after authorized official dependency acquisition. All
existing smoke families passed; the new resolver smoke passed four times
(both pairs, normal `-I` and optimized `-O -I`) with **27 explicit checks**
each, including real mapper/inference composition. Optimized checks do not
rely on assert statements.

Later PR-number, provenance and handoff edits are documentation-only and do
not rebuild or relabel this historical clean-source provenance. CI results
must be attributed to their own tested head.

No Windows, live HA/device, physical write, deployment, durable runtime,
BUG-033 repair or Feature/R1 certification is inferred from these checks.
