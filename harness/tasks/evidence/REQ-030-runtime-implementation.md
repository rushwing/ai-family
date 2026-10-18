# REQ-030 / HI-S017 proposed event-application delivery

## Authority and behavior

[human-001][2026-10-18] Instructed “resume the last session and continue with
the task you suggested.” The previous suggestion admitted HI-S017 as REQ-030,
with proposed specification/TC text, implementation and a draft PR for external
review. Generator-001 consolidated two interrupted sessions' overlapping edits;
no independent Planner/Evaluator signatures or final acceptance are inferred.

Clean implementation source `6c02c062e84daef9171128b49b3012cd7e0cb5e7`
adds `CurrentStateStore.advance_epoch` and `apply` under the existing snapshot
publication lock. Exact trusted write scope precedes metadata, lookup and
payload inspection. Epochs are explicit per-home owner allocations and cannot
regress below a pin or any stored report/availability/intent baseline. Pinning
does not rewrite observations, revisions or freshness, and homes are independent.

Canonical normalized deltas carry no desired intent and require pinned-epoch
ordering. Shared per-member ordering merges newer members, ignores stale ones,
preserves omitted reports/intent and atomically rejects conflicting typed replay.
Wrong generations fail even when stale. No-op replay/stale input retains revision
and ingestion time; newer equal-valued observations increment once. Real
normalizer output exercises offline, unknown, removal and recovery transitions.
Source timestamps never substitute for ordering; ACKs are not observations.
Private parser exceptions are neither retained as context nor formatted in errors.

Grants/context remain trusted composition inputs rather than authentication.
The owner must coordinate one source-ordering domain per home across providers,
allocate a new epoch when sequences reset, and restore generations after restart.
Provider loops, durable epochs, snapshot/live-event reconciliation, query/API
services, device actions and BUG-033 remain separate work.

## Executed verification

Linux aarch64 / CPython 3.12, source 6c02c06:

- **1,290 required fabric and 1,795 required shared tests pass**, zero failures,
  errors or skips. Fabric uses all eleven required-runtime flags. JUnit hashes,
  exact expected counts and per-TC totals are retained in the provenance below.
- **164 application cases** across both recovered test suites plus nine
  hermetic absent/broken/missing-method/missing-dependency/skip gate probes.
  Overlapping TC-030-01/02/03/04 groups execute **98 / 36 / 27 / 13** cases.
  Cases cover scope, strict input/error priority, independent member ordering,
  conflicting replay rollback, snapshot/event/rebuild concurrency, epoch races,
  cross-device/home fences, retained intent/reports and immutable detached views.
- **Nine runtime mutations detected** by assertion failures, with no timeout:
  write-grant bypass, replay publication, event epoch fence, stored epoch floor,
  pin regression, lost desired intent, omitted report loss, double revision and
  clock-priority bypass. The report-retention mutation exposed a missing
  assertion; the final test explicitly checks every omitted report is retained.
  The exact harness, selections, summaries and log hashes are recorded below.
- The CI wiring test removes each of eleven required flags and rejects each
  omission, disabled job and echo-substituted pytest command. CI expects exactly
  1,290 fabric tests; required-mode skips fail the suite.
- Ruff, strict mypy (15 runtime source files), all governance scripts,
  **21 planning regressions**, public-data/requirements validation, secret scan
  and whitespace pass. All 51 local Markdown links in the implementation diff
  resolve. AST inspection finds no duplicate runtime methods or test hooks.

The earlier interrupted run's NameError failures came from overlapping test
hooks. Sandbox-denied loopback sockets required an authorized regression rerun.
Neither failed run is counted as passing evidence.

## Fresh installed packages

The builder records `source_dirty:false` at 6c02c06. Both shared/fabric direct
wheel and sdist-derived wheel pairs build and install in fresh isolated
environments. Eight downloaded dependency wheels are verified against official
release metadata before installation, with environment/proxy overrides disabled.
All existing installed smoke families pass. Both new smoke programs run on
both package pairs under `-I` and `-O -I`: **eight new smoke executions, each
18 explicit checks and offline:true**. Test-only sibling fixtures load through
explicit paths; runtime imports resolve from installed distributions.

[Machine-readable source/artifact provenance](REQ-030-artifact-provenance.json)
retains source/runtime/JUnit/dependency/artifact/test hashes, interpreter and
platform identities, smoke results and mutation evidence. Evidence follow-up
changes no tested runtime, test, dependency, smoke or CI bytes.

## External review boundary

[REQ-030](../features/REQ-030.md) remains req_impl / generator-001, review_round 0,
AC1–AC4 unchecked and TC-030-01–04 implemented. [Draft PR #61](https://github.com/rushwing/ai-family/pull/61) requests external
review; no independent approval or merge is inferred. Local Python 3.13/3.14,
Windows/Termux, private HA or hardware results are not claimed. The configured
three-version CI matrix provides separate verification. Human acceptance,
BUG-033 and Feature/Stage completion retain their own gates.
