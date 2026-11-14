# REQ-003/004 shared prerequisite review handoff

Prepared by generator-001 on 2026-11-14. Runtime and proposed criteria commit:
`0599c9f6ae8abb6437ff5a5e21e0d6ecab927ae6`, after REQ-039 admission commit
`ddb254d` on merged main `fec13be`. This document and the linked provenance
are a later documentation-only evidence increment.

Human-001 authorized bounded shared work under
[REQ-003](../features/REQ-003.md) and [REQ-004](../features/REQ-004.md).
Both remain `req_impl / generator-001`; new criteria remain generator-authored
drafts. No independent TC approval, evaluator signature or full REQ acceptance
is asserted. [REQ-039](../features/REQ-039.md) remains blocked pending the shared
evidence review and human restoration of its design handoff.

## Delivered behavior

- [Migration 0006](../../../data/migrations/0006_gateway_confirmation.sql)
  extends existing confirm_token with a versioned gateway protocol and adds
  member-isolated nonce claims. Existing check-in rows retain their protocol.
- [PostgresConfirmStore](../../../toolsets/mcp/gateway/gateway/persistence.py)
  atomically claims a signed proof nonce and issues a payload/session/member/tool
  bound token. Tokens are stored as hashes. Consumption has one winner across
  independent connections/processes, uses database expiry, and never falls back
  to memory on persistence errors. Failed issuance rolls back the nonce claim.
- [AuthenticatedTool](../../../toolsets/mcp/gateway/gateway/tools.py) rechecks
  the original JWT and current policy, isolates the actual handler connection
  with transaction-local aifam_app/member scope, and detaches claims/parameters.
  home.execute_action is registered for admin/adult with user confirmation;
  missing durable storage or wrapper wiring keeps issuance/execution unavailable.
  A generic Goal executor cannot enable it. Final tool-entry policy denial or
  failure returns a redacted 403/503 and makes zero handler calls.
- [CI](../../../.github/workflows/ci.yml) supplies PostgreSQL 16, runs the
  required suites, uploads JUnit and rejects absent/skipped/failing prerequisite
  suites. Migration and result-gate changes trigger the MCP job; the result
  gate's own negative regressions also execute there.

The [gateway README](../../../toolsets/mcp/gateway/README.md) specifies setup,
trust boundaries, timeout behavior, nonce retention and rollback. A consumed
confirmation remains consumed after handler failure; this is not durable task
delivery. The default Goal-only boundary retains its bounded local test mode.

## Executed verification

Linux aarch64, CPython 3.12.12, PostgreSQL 17.12 and psycopg 3.3.9. A dedicated
local PostgreSQL server supplied a fresh randomly named database; all six
migrations ran twice, and the fixture dropped that database afterwards.

| Check | Result |
| --- | --- |
| Full Goal manifest and gateway suite | 130 passed, 14 legacy environment skips |
| Required test_confirmation_pg | 12 passed, zero skips/errors/failures |
| Required test_registered_home | 39 passed, zero skips/errors/failures |
| GoalAgent legacy direct-route regressions | 3 passed |
| Result-gate negative regressions | 2 passed |
| scripts/check.sh | Passed, including 21 planning regressions |
| Public-data scan, Ruff and git diff whitespace checks | Passed |
| Both MCP packages, sdist and wheel-from-sdist builds | Passed |

[Provenance](REQ-003-004-prerequisite-provenance.json) records the exact source
commit, source/artifact hashes, final JUnit digest and all 51 required passing
case names. Local JUnit: `/tmp/req003-004-results.xml`; artifacts:
`/tmp/req003-004-artifacts/`. These paths are local execution outputs, not hosted
CI artifacts. Remote CI has not been run for this delivery.

Reproduce using a disposable PostgreSQL administrator DSN:

```bash
AIFAMILY_CONFIRMATION_TEST_DSN='<disposable test database DSN>' \
AIFAMILY_REQUIRE_CONFIRMATION_PG=1 \
python -m pytest toolsets/mcp/goal-mcp/tests toolsets/mcp/gateway/tests -q \
  --junitxml=/tmp/mcp-boundary-results.xml
python tools/check_gateway_results.py /tmp/mcp-boundary-results.xml
python -m unittest discover -s tests -p test_gateway_results.py
python -m pytest agents/goal/tests/integration/test_legacy_direct_disabled.py -q
```

Initial reruns used incorrect local socket/role settings and failed during
database setup. Correcting the disposable connection and running outside the
sandbox produced the final results above. The legacy async SQLite fixture also
required execution outside the sandbox. Missing Goal test dependencies were
installed in the disposable environment before its passing run.

## Review criteria and remaining gates

| Proposed TC | Evidence to assess independently |
| --- | --- |
| [TC-003-11](../test-cases/TC-003-11.md) | 16-way proof/token races, new-process proof/token replay, exact binding, expiry, rollback, RLS and database-outage denial |
| [TC-004-01](../test-cases/TC-004-01.md) | Registration metadata denial; actual fixture RS256 verification; kid/member/device isolation, detached metadata, current policy and transaction-local RLS |
| [TC-004-02](../test-cases/TC-004-02.md) | Home registration, missing/memory-only wiring, ordinary bearer self-confirmation denial, altered proofs, cross-app replay, final policy checks and zero counted handler calls |

The 14 skipped tests are legacy external gateway/IdP cases; fixture RSA keys
replace JWKS fetching for the new tests. Neither live IdP nor live PostgreSQL 16
certification is claimed. The local PG17 run does not replace the configured
PG16 CI execution. Builds are packaging checks, not installed-artifact runtime
certification. No provider or production home handler is connected.

An independent evaluator must review the proposed TC criteria before judging
coverage, record the exact reviewed head and executed environments, and assess
the shared prerequisite contract. Human-001 then decides whether to restore
REQ-039 via T17 for design refinement. Canonical validation, availability and
production member/device policy remain the REQ-039 guard's work. Full Goal
handler migration, durable audit, governed tasks, physical dispatch, deployment,
readiness and final merge remain outside this bounded delivery.
