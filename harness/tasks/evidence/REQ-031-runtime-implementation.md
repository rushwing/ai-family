# REQ-031 / HI-S013 proposed read-only discovery delivery

This is the historical implementation record for source `47a1a7d`. The subsequent
[F1/F2 response](REQ-031-review-fixes.md) records amended source `16d0fe4`,
1419 fabric passes, 113 discovery cases and the additional mutation checks.

## Authority and implementation

[human-001][2026-10-18] Instructed “continue with your suggestion” after the
HI-S013 / proposed REQ-031 recommendation following PR #62. Generator-001
prepares the specification, proposed TC text/code and implementation for combined
external review, following the prior increment. No independent lifecycle
signature or final acceptance is inferred.

Clean source `47a1a7df4ea856590c25ef2395fe39a0ca7b115e` adds a separate
HARegistryDiscoveryClient with exact explicit configuration/limits and no
constructor I/O. Each discover authenticates a fresh owned WebSocket and sends
only four serial read-only commands: device/entity/area registry lists and
get_states. It reuses accepted no-redirect/no-proxy/TLS-trust/wire-log policy
without changing any accepted runtime module or REST/subscription public API.

One operation deadline covers connection, authentication, all reads and parsing;
cleanup is separately bounded to one second and aborts on failure. Concurrent
calls fail client_busy, calls after close fail client_closed, event-loop binding
is explicit, and cancellation/close drain owned work. There is no automatic
retry; an owner may explicitly invoke a new call after a failed acquisition.
Process-control exceptions propagate after resource cleanup.

Strict text/UTF-8/JSON envelopes, unique result IDs/record identities, record
shapes and byte/depth/count bounds reject malformed peers. Escaped unpaired
surrogates in both keys and values are rejected. Explicit component failure
stops later commands and never becomes an empty success or partial bundle.
Errors expose finite code/stage/completed labels without raw exception context
or peer text. Immutable results expose count-only summaries; for_mapping is
the deliberate detached private-data export for trusted adapter code. Repr is
constant and raw serialization/copy is refused.

Complete means four successful credential-visible reads. HA may filter current
states without an error; serial registries can change between reads. This is
not global permission proof, an atomic HA snapshot, physical freshness or
canonical mapping. Registry mapping, capability inference, store publication,
reconnect reconciliation, query/API services and device actions remain separate.
The REQ links official protocol/core references checked during design.

## Executed verification

Linux aarch64 / CPython 3.12.12, clean source 47a1a7d:

- **1414 required fabric + 1795 required shared passes**, zero failures/errors/
  skips. All twelve fabric runtime flags are supplied, and CI enforces the exact
  1414 count. JUnit hashes, expected/actual counts and per-TC results are retained
  in the provenance below. TC-031-01/02/03/04 execute **20 / 69 / 30 / 12**
  overlapping cases.
- **108 discovery cases** plus **ten hermetic required-runtime gate probes**
  cover exact input types/limits, complete and empty views, preserved unknown
  provider fields and mismatched registry/state sets, partial permission and
  unsupported commands, strict framing/Unicode/IDs/records, shared deadlines,
  no retries, transport/HTTP/auth/remote-close failures, busy/closed/wrong-loop
  admission, repeated cancellation, close during connection, cleanup failures/
  abort, process-control propagation, and real authenticated loopback discovery.
- **Twelve runtime mutations detected by assertions**, with no timeout-based
  kill: a write command, auth-rejection bypass, mismatched result ID, duplicate
  record identity, byte/count limits, ignored cleanup failure, raw exception
  context, concurrent admission, deadline reset, private repr and escaped
  surrogate retention. Exact harness, selections, mutant/log hashes and failure
  summaries are recorded below. The CI guard separately rejects each of twelve
  missing flags, disabled job and echo-substituted pytest command.
- Ruff, strict mypy (**16 runtime sources**), all governance scripts,
  **21 planning regressions**, public-data/requirements validation, secret scan
  and whitespace pass. All **49** implementation Markdown links resolve.
- All accepted runtime modules, shared contracts and historical evidence JSON
  remain byte-identical to merged main. Only the new discovery runtime is added;
  test/build/CI and Story navigation changes support this increment.

The earlier overlapping-load full run recorded **2 failures / 1412 passes** in
accepted REST tests test_real_overall_deadline_headers_and_trickle[False/True].
Both returned the expected timeout but their fixture server observed zero
requests before the 80ms deadline. That run overlapped mutation subprocesses;
its cause is not conclusively attributed. Accepted REST code/tests were not
changed. The final clean-source run without overlapping mutations passed every
case, including both failures. The failed run's hash is retained separately and
is never counted as passing evidence.

## Fresh installed packages

The builder records source_dirty:false at 47a1a7d. Both shared/fabric direct and
sdist-derived wheel pairs build and install into fresh isolated environments.
Eight dependency wheels are verified against official release metadata before
installation. All existing smoke families pass. The new real loopback discovery
program executes on both pairs under `-I` and `-O -I`: **four executions, each
15 explicit checks, loopback:true and device_writes:0**. It checks wire command
order, exact credential use, detached/private results, repeated calls, partial
permission rejection, empty success, close and resource release. Explicit
conditions survive optimized Python.

[Machine-readable provenance](REQ-031-artifact-provenance.json) retains source,
runtime/JUnit/test/dependency/artifact hashes, interpreter/platform identities,
smoke outcomes and mutations. Evidence follow-up changes no tested runtime,
test, dependency, smoke or CI bytes.

## External review boundary

[REQ-031](../features/REQ-031.md) stays req_impl / generator-001, review_round 0,
AC1–AC4 unchecked and TC-031-01–04 implemented. [Draft PR #63](https://github.com/rushwing/ai-family/pull/63) requests external
review. No independent approval, human acceptance, merge, BUG-033 resolution or
Feature/Stage completion is inferred. Local Python 3.13/3.14, Windows/Termux,
private HA/hardware and long-soak results are not claimed; the configured CI
matrix supplies separate version/package verification.

## Session recovery verification — 2026-10-19

[generator-001] Verified that every recorded source hash matches implementation
commit `47a1a7df4ea856590c25ef2395fe39a0ca7b115e`. Runtime, tests, smoke programs,
dependencies and CI files remain unchanged. Checked the retained provenance's
test totals, eight dependency hashes, twelve mutation outcomes and four discovery
smoke outcomes, and resolved all nine local links in this record and REQ-031.
All nine governance/requirements scripts and all 21 planning regressions pass
again. These are evidence-integrity and governance checks; the historical local
runtime, mutation and installed-package runs above were not repeated.

GitHub [CI run 39093440365](https://github.com/rushwing/ai-family/actions/runs/39093440365)
passes for that implementation commit, including both shared and fabric jobs on
Python 3.12, 3.13 and 3.14. All eleven executed checks succeed; the two unrelated
web/requirements jobs are skipped by their path filters. This CI result is
separate from the original local aarch64 execution evidence.
