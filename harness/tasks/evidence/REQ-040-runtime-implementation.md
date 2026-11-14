# REQ-040 implementation handoff

Human-001 authorized HI-S023 admission and combined specification, proposed
TC text/code, implementation and verification, stopping at
`req_impl / generator-001` with [draft PR #84](https://github.com/rushwing/ai-family/pull/84).
[REQ-040](../features/REQ-040.md) retains six unchecked acceptance criteria;
TC-040-01–04 remain generator-authored drafts. External combined review must
assess the requirement, test design/code and implementation. No independent
T03/T07/T10/T13 signature, acceptance, ready, merge or archival is asserted.

## Delivered behavior

Migration 0007 adds versioned, typed append-only `audit.home_action_event`
records with database time, random attempt/event UUIDs and domain-separated
HMAC correlation references. Raw payloads, credentials, proofs, tokens,
arguments and exception text are excluded. Reapplying the migration preserves
rows. PostgreSQL FORCE RLS and role privileges enforce member reads, anonymous
row isolation and denied UPDATE/DELETE/TRUNCATE for application, kid and audit
reader roles. Oversight reads require verified adult/admin identity, a separate
configured DSN and an exact-True trusted approval callback.

Explicitly injected gateway audit middleware covers the registered home tool
and its independent confirmation route. It commits `started` before route
delegation, then records the actual HTTP boundary outcome. Persistence errors
return fixed `audit_unavailable` / 503. Terminal-write failure retains the
committed start as uncertain evidence; business rollback cannot erase it.
Independent retries retain correlation while appending distinct events.

An allowed confirmation means proof acceptance. Audit does not authorize
physical action. The accepted guard still leaves physical entry disabled;
consumed confirmation remains consumed after rejection. Future task/outbox and
dispatch integration must preserve protected authority/state checks and handle
uncertain physical effects separately. Omitted audit preserves the existing
boundary compatibility without certifying durable-audit readiness.

## Executed evidence

[Provenance](REQ-040-artifact-provenance.json) pins implementation commit
`57f36acf1e6b8ab4e116cb8161ce43a0f6c70a51`, source hashes, JUnit hash, every
required test identity and all 40 distribution/dependency hashes.
[CI run 43579933475](https://github.com/rushwing/ai-family/actions/runs/43579933475)
tested GitHub's synthetic merge `353a114a9b1a7bd05820e7687398e7448dad3e0d`.
Its complete tree is identical to the implementation tree; its parents are
the admitted base `3146281` and implementation `57f36ac`. The original installed
provenance retains the synthetic merge SHA rather than relabeling its artifacts.

- MCP/Goal/gateway: **311 passed, 14 skipped**, zero failures/errors. The skips
  are the existing external gateway/IdP suites (nine write, five JWT cases).
- Required identities: **232 passed without skips**, retaining the prior 149
  and adding **83 audit cases**. The downloaded JUnit passed the required-result
  gate again on recovery; all eight gate regression tests also passed locally.
- Real PostgreSQL 16 tests cover append-only privileges/RLS, cross-member reads,
  oversight approvals, multi-instance/process correlation, committed start
  before delegation, real permission/trigger/lock failures, missing schema,
  terminal failure, private-error suppression and confirmation/guard regression.
- Four installed audit runs: **25 explicit checks each**, direct and
  sdist-derived wheels, normal and optimized Python. Four existing installed
  guard runs also passed **19 checks each**. All run outside the checkout with
  dispatch disabled. SQL migrations are supplied from the checkout; the wheels
  package Python runtime code, not deployment SQL.
- CI Ruff and strict guard/audit mypy passed, as did the three Goal legacy-route
  tests. Overall CI: **14 successful jobs, two path-filtered skips**.
- Recovery governance passed, including 21 planning and two Harness-link
  regressions. The source and artifact evidence remains pinned to the
  implementation; subsequent documentation commits do not relabel that run.

CI used Linux x86_64, CPython 3.12.16 and PostgreSQL 16. Tokens carry real RS256
signatures; fixture JWKS retrieval replaces network lookup. Data and identities
are fictional. This supplies generator evidence, not live IdP/HA/household,
production authority, deployment or independent acceptance certification.

## Recovery and review boundary

The previous session was interrupted after committing implementation and
creating PR #84. A machine restart removed temporary local PostgreSQL,
environments and reports. Recovery downloaded the successful CI artifact,
verified every recorded distribution digest and required case, checked the
test-merge tree against the implementation, and attached this single handoff
and provenance pair. Lost local artifacts are not claimed as recovered; no
local runtime rerun is asserted after the restart.

Review remains external at req_impl. Production policy administration,
task/outbox/idempotency execution, physical dispatch, deployment, full
REQ-003/004 completion and Feature/Stage acceptance remain separate work.
