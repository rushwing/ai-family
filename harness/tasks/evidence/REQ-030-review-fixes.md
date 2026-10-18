# REQ-030 local pre-review fixes A–D

The user supplied a local pre-review of draft PR #61 at eebfda58 and instructed
“Fix all findings.” This follow-up records generator changes and execution,
without treating the report as T03/T07/T10/T13 approval or final acceptance.
The original implementation evidence and all historical evidence JSON remain
unchanged.

## Disposition

- **A — gate infrastructure:** `run_probe` retains a finite deadline, raised
  from 30 to 90 seconds for loaded hosts. `TimeoutExpired` now produces an
  explicit failure with command and captured stdout/stderr, decoding partial
  byte output safely and labeling missing output. Three deterministic tests
  exercise byte/text/absent streams. There is no retry and no timeout-to-pass
  conversion. The reported initial transient failure was not reproduced here;
  load-related timeout remains a hypothesis, not an established root cause.
- **B — provenance boundary:** the REQ, README and `apply` docstring now state
  that canonical DeviceState JSON has no delta/origin marker. Valid snapshots
  and normalized deltas are indistinguishable and use the same merge semantics.
  Raw ACK envelopes fail schema validation, but callers must admit verified
  observations and route ACKs separately. A future enforced marker would need
  separately admitted shared-contract work. No marker/authentication guarantee
  is claimed or added in this increment.
- **C — canonical errors:** parsing the shared merge result remains necessary
  to construct the immutable typed snapshot. It now runs inside the same
  StateError handler as merging. Any malformed result becomes fixed-path
  `invalid_event`, raised outside the handler so canonical context is absent,
  before publication. Three injected malformed-result cases verify privacy,
  unchanged input/state/revision/time/pin, and successful next publication.
- **D — scan cost:** the runtime comment and README explain the actual linear
  scan of all registered rows plus this home's stored member orders, under the
  publication lock. Deriving the floor from current rows covers trusted
  `put`/`rebuild` changes. No separate cache or speculative optimization is added.

## Executed verification

Clean source `ca9745c404c8d619d31f3b31139fd4cf9c427405`, Linux aarch64 /
CPython 3.12.12:

- **1,296 required fabric + 1,795 required shared passes**, zero failures,
  errors or skips. CI's exact expected fabric count is now 1,296 and retains
  all eleven required flags. **167 application cases**, nine runtime-gate probes
  and three timeout-diagnostic cases execute. Overlapping TC-030-01/02/03/04
  counts are **101 / 36 / 27 / 19**.
- The six new cases pass independently; application-events plus the full gate
  module also pass (**162 cases**). Ruff, strict mypy (15 runtime sources),
  governance and 21 planning regressions pass.
- **Ten runtime mutations detected:** the original nine behavioral mutations
  rerun on this runtime plus a merged-parser escape mutation. A separate
  mutation removing timeout diagnostics fails all three timeout cases.
  Exact mutation harnesses, summaries and log/source hashes are recorded in
  [review-fix provenance](REQ-030-review-fixes-provenance.json).
- Fresh direct and sdist-derived shared/fabric wheel pairs build and install
  with eight officially verified dependency wheels. All installed smoke families
  pass. Both new programs execute under normal/optimized isolated Python on
  both pairs: **eight executions, each 18 checks and offline:true**. The builder
  records `source_dirty:false` at ca9745c and retains JUnit/source/artifact hashes.
- Seven accepted provider modules and all pre-existing evidence JSON are
  byte-identical to eebfda58. Shared contracts are unchanged. Evidence follow-up
  changes no tested runtime, test, smoke, dependency or CI bytes.

Local Android/Termux, Windows, private HA, hardware and long-soak behavior were
not rerun. Python 3.13/3.14 remain separately verified by the PR CI matrix.
The user-supplied Termux results remain attributed to that report.

## Review boundary

[Draft PR #61](https://github.com/rushwing/ai-family/pull/61) remains open/draft.
[REQ-030](../features/REQ-030.md) stays req_impl / generator-001, review_round 0,
AC1–AC4 unchecked and all four TCs implemented. No independent evaluator
signature, final human acceptance, merge, BUG-033 or Feature/Stage completion
is inferred from this fix delivery.
