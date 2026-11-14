# REQ-039 combined implementation review handoff

Human-001 supplied a non-signing local pre-review of PR #82 and instructed
“Fix all findings. And then continue to implement. stop after req_impl for
external review”. This explicitly authorizes the generator's combined design
revision, proposed draft criteria, runtime and verification. It supersedes the
previous design-only handoff; it does not invent independent T03/T07/T10/T13
signatures or final acceptance.

[REQ-039](../features/REQ-039.md) remains **req_impl / generator-001**, eight
unchecked ACs and four draft TCs. [PR #82](https://github.com/rushwing/ai-family/pull/82)
remains draft for external combined review. No production authority/provider,
physical dispatch, deployment, Feature acceptance or full REQ-003/004 completion
is claimed. Review the proposed criteria before judging their implementation.

## Exact delivered source

Implementation commit: `903e8138c0e593d1638580c4858b4b03fad67665`, on design
head `35d7cae`, based on main `382ebbb` (PR #81). Later delivery evidence is a
documentation-only increment. [Provenance](REQ-039-implementation-provenance.json)
pins changed runtime/test/CI/manifest hashes, JUnit digests, all required test
identities, five killed behavioral mutations and rebuilt artifact/dependency
hashes from that clean source commit. Historical evidence JSON remains unchanged.

`gateway.home_guard.HomeActionGuard` reuses the existing JWT verifier,
AuthenticatedTool, shared PG proof/token machinery, canonical factories and
REQ-037 ActionValidator. It accepts exact raw canonical business payloads and
server-owned configuration/authority. Assessment exports only status/reason and
cannot be submitted as permission. `as_tool()` supplies preflight and protected
final-handler composition for the registered home tool. The default app has no
injected guard/authority; even an eligible confirmed composed entry returns
fixed 503 without a task/executor/provider sink.

`CurrentStateStore.capture_lease()` v1 holds the existing publication lock and
exposes current committed epoch/inventory and a live view; captures expire on
exit. Existing put/apply/rebuild/reconciliation/epoch/invalidation writers all
participate in that same lock. The guard first holds the trusted authority's
PG principal/grant/binding/generation protections, then the state capture, and
rechecks canonical semantics plus independently aged availability. Finite waits
and post-wait JWT expiry apply. Fixture authority adapters hold real PG row
locks and RLS; no production policy table, administration API or distributed
state authority is installed. Adapter writers must share the specified protocol;
unsupported distributed composition fails closed.

## Findings disposition

| Finding | Delivered disposition |
| --- | --- |
| F1 | Explicit ordered state machine: unknown/ungranted targets are forbidden before descriptive lookup; granted unknown inventory/generation/binding mismatches are guard_unavailable. REQ-037 unknown_home/device never escape the guard. Combined-fault tests count/deny premature validator lookup. |
| F2 | GuardDecision validates a complete finite status/reason vocabulary. Post-grant semantic visibility, safe adapter mappings and conservative current-wrapper collapse are explicit. |
| F3 | Direct Inventory dependency REQ-013 added. Direct bounded _json import also declares REQ-032. |
| I1/I2 | T17/T02 remain historical; later explicit combined authority assigns generator ownership without independent approval. Accepted shared prerequisites are reused without marking full REQ-003/004 done. |
| I3 | Concrete capture-lease v1 API, committed epoch access, lock order, expiry and participating-writer contract are implemented and tested with barriers and actual PG lock dependencies. |
| I4/I5/I6 | Single-store scope is explicit; distributed composition is unavailable, resource waits remain bounded, TCs remain draft and existing MCP CI is not relabeled as independent approval. |

The local pre-review evaluated the design and could not execute an absent guard
runtime. Its positive observations remain reviewer-attributed, non-signing
observations; the executions below are generator checks of the implementation.

## Executed verification

Linux aarch64, CPython 3.12.12, PostgreSQL 17.12 and psycopg 3.3.9. Fixture RSA
keys replace external JWKS retrieval; actual RS256 verification executes.
Dedicated random PG test databases apply migrations twice and are dropped.

| Verification | Result |
| --- | --- |
| Full MCP manifest/gateway | 228 passed, 14 legacy external gateway/IdP skips |
| Required original prerequisite identities | 63 passed, zero skips |
| New guard identities | 86 passed, zero skips |
| Exact required-case gate | All 149 identities exactly once and passing |
| Gate negative regressions | 8 tests passed, including omission of every required identity |
| Full fabric suite with all eighteen required-runtime flags | 2,163 passed, zero skips/errors/failures |
| GoalAgent legacy direct routes | 3 passed |
| Ruff, strict mypy guard + 22 fabric modules | Passed |
| Governance, planning regressions, public-data/requirements and whitespace | Passed, including 21 planning regressions |
| Local distributions | 12: direct wheels, sdists and sdist-derived wheels for schema/fabric/goal/gateway |
| Fresh isolated installed PG smokes | Four passed, 19 explicit checks each; direct/derived sets, ordinary and -O, all -I outside checkout |
| Isolated behavioral mutations | Five killed by assertions, zero setup errors |

The source tests cover signed identity/member/action isolation, F1/F2 ordering,
strict JSON/configuration, semantic allowlist, missing/old/future/stale/epoch
observations, fresh property with old availability, clock failure/regression,
post-wait token expiry, capture release/timeout, every existing state writer,
preflight rejection before proof claim/token consumption, cross-app proof replay,
concurrent token single-winner consumption, final revoke/rebind/generation/
disconnect races and permanently disabled physical dispatch. The PG race probe
queries pg_blocking_pids to prove a revoker waits while the final fixture entry
retains its protections; ordering is not based on a sleep. Counted fixture sinks
are patched into tests only; production has no sink option.

Mutations remove exact-grant denial (4 failing cases), skip final protected
entry (4), ignore independent availability age (2), infer an uncommitted epoch
from observations (1), and accept a forged initial descriptor (1). Each runs in
an isolated full-package copy with an asserted import origin; tracked runtime
is unchanged. Counts are failing assertions, not distinct acceptance approvals.

The first packaging attempt lacked pip in the disposable environment, and an
unbounded initial dependency download was interrupted. Installing pip and
using bounded retries produced the final four passing smokes. The initial age
mutation selected a row-freshness test and survived; selecting the actual
independent-availability cases killed it. Final mutation evidence records only
completed assertion failures with zero setup errors. No runtime bug or approval
is concealed by those environment/probe corrections.

## Proposed criteria and external review

- [TC-039-01](../test-cases/TC-039-01.md): signed identity, exact grants, ordered reason visibility, canonical semantics, strict configuration and redaction.
- [TC-039-02](../test-cases/TC-039-02.md): independent availability age/epoch and retained capture barrier across all writers, release and finite waits.
- [TC-039-03](../test-cases/TC-039-03.md): real-PG gateway confirmation/final-entry composition, concurrency/replay/revocation and zero physical effects.
- [TC-039-04](../test-cases/TC-039-04.md): required-case gate, source/installed artifacts, missing/broken seams, compatibility and evidence limits.

These groups overlap. External review must assess the proposed criteria,
resource-authority trust and writer-participation contract, bounded single-store
support, failure privacy/order, final scope and all eight unchecked ACs against
its reviewed exact head. The guard accepts no caller-supplied context or
eligibility object as authority. Default no-dispatch behavior is intentional,
not an accepted TaskResult or physical convergence claim.

CI installs local schema/fabric dependencies and triggers MCP on their changes.
It requires all 149 pinned identities, strict guard typing and four installed
PG smokes, with JUnit/distribution/provenance uploads. Final-head PG16 CI results
are attached to PR #82 separately after execution; local PG17 is not relabeled
PG16. There is no live IdP/HA/device or production distributed-policy certificate.

Local JUnit: `/tmp/req039-final-mcp-results.xml`, `/tmp/req039-fabric-results.xml`.
Artifacts: `/tmp/req039-final-artifacts/`; mutation logs: `/tmp/req039-mutations/`.
Reproduce the MCP run with a dedicated AIFAMILY_CONFIRMATION_TEST_DSN and
AIFAMILY_REQUIRE_CONFIRMATION_PG=1, then run tools/check_gateway_results.py.
Use tests/build_guard_artifacts.py with an outside-checkout output directory
and a dedicated administrator DSN for fresh installed-package PG checks.

Stop at req_impl for external review. Confirmation remains consumed after a
final denial/unavailable response. Trusted production policy, durable audit,
governed task/idempotency/outbox and physical execution retain separate gates;
no automatic token restoration, hidden executor or merge follows this delivery.

Documentation-only evidence checks passed: 91 local Markdown links, all nine
recorded runtime/test/CI source hashes, byte-identical preservation of all
139 prior evidence files, and req_impl/draft/unchecked-AC lifecycle invariants.
