# REQ-039 implementation handoff

Human-001 authorized fixes and combined implementation, stopping at
`req_impl / generator-001` for external review in [draft PR #82](https://github.com/rushwing/ai-family/pull/82).
[REQ-039](../features/REQ-039.md) retains eight unchecked ACs and four draft TCs.
No independent evaluator signature, acceptance or merge is asserted.

## Delivered behavior

F1/F2 now define the ordered pre-grant/post-grant state machine and finite
reason vocabulary. F3 declares REQ-013; direct JSON reuse also declares REQ-032.
HomeActionGuard verifies the original bearer, exact scoped authority, canonical
request and allowlist, current binding/generation, independent availability age
and committed epoch. Final entry repeats checks while retaining PostgreSQL
row protections and the CurrentStateStore publication lock, acquired DB first.
The version-1 capture lease expires on exit and shares the existing writer lock.
Authority fixtures support one explicitly fenced store; distributed authority
and production policy adapters remain deployment gates.

The registered wrapper composes shared PostgreSQL confirmation consumption with
final checks. Revoke, rebind, generation changes and disconnects after preflight
are rejected. Consumed tokens remain consumed after final rejection. Eligible
production entry still returns fixed 503: physical dispatch, governed task and
durable audit composition remain unavailable.

## Executed source evidence

[Provenance](REQ-039-artifact-provenance.json) identifies implementation commit
`903e8138c0e593d1638580c4858b4b03fad67665`, exact source and JUnit hashes,
required test identities, five killed mutations and installed artifact digests.
Source runs used CPython 3.12.12 / Linux aarch64 / PostgreSQL 17.12 and fixture
RS256 tokens; external JWKS retrieval was replaced.

- MCP: 228 passed, 14 legacy external gateway/IdP cases skipped, no failures/errors.
- Required gateway cases: all original 63 plus 86 guard cases, 149 passed without skips.
- Fabric: 2,163 passed, no failures/errors/skips.
- Five killed faults: skipped exact grant, skipped final entry, ignored availability
  age, inferred epoch from snapshot and accepted forged descriptor.
- Direct and sdist-derived wheel sets: normal and optimized Python, four runs
  from outside checkout, 19 explicit checks each, dispatch disabled throughout.

Tests exercise real PostgreSQL grant/binding row locks and confirmation storage,
concurrent revoke/rebind and state publication, wait-time aging/JWT expiration,
exact confirmation binding/replay and no physical calls. These are generator
checks against draft criteria, not independent approval.

On session recovery the retained JUnit reports, required-case manifest, mutation
clean-source hashes and every packaged artifact digest were rechecked.
Governance gates and all 21 planning regressions passed again. Final CI uses
PostgreSQL 16 and must be attributed to its own PR head, separately from this
source-specific PostgreSQL 17 evidence. Later evidence/docs-only commits do not
relabel the implementation artifacts.

## Second-round review follow-up

F4: the combined-delivery paragraph now links the committed runtime handoff
and artifact provenance above. Active Harness requirement links are checked by
local governance and CI against committed paths, so an untracked local evidence
file cannot hide a missing delivery artifact. No historical evidence is rewritten.

I9/I10: this slice holds one store-wide publication lock across all homes for
a bounded wait of up to five seconds; contention can block unrelated home reads
and writes. Each authorization preflight opens a PostgreSQL connection and
authority lease, repeated at app boundary, wrapper authorization and protected
final entry. Connection and latency optimization and finer lock granularity are
future work and must retain the final-entry guarantees. I7/I8/I11/I12 require no
behavior change; the review and acceptance boundary remains unchanged.

## Third-round review follow-up

F5/I16: removed the two unreferenced implementation-named evidence duplicates.
This runtime handoff and its linked artifact provenance remain the single
REQ-linked evidence pair. The original artifact provenance is preserved byte
for byte, including historical local JUnit paths; its source commit and hashes
identify the recorded evidence. No parallel provenance copy is maintained.

I13/I14: the link gate intentionally covers inline local links in the ten active
requirement files and requires a Git checkout. Evidence, TC and story links and
source tarballs without Git metadata remain outside that gate's stated scope.
I15: the existing contention and connection-cost notes above remain applicable;
no runtime behavior or lifecycle status changes in this follow-up.
