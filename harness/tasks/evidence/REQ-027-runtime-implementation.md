# REQ-027 / HI-S005 proposed subscription delivery

This original source-specific execution record remains historical. The
[local pre-review remediation](REQ-027-review-fixes.md) and
[fresh repair provenance](REQ-027-review-fixes-provenance.json) supersede the
active verification baseline with bounded smoke-failure cleanup and 873 tests.

[human-001][2026-10-17] Instructed “proceed with HI-S005” after the proposed
REQ-027 increment and separate draft PR for external review. [generator-001]
delivers the admitted specification, proposed TC text/code and implementation
in draft [PR #56](https://github.com/rushwing/ai-family/pull/56).

## Behavior and boundaries

HAStateSubscriptionClient reuses REQ-024's owned socket, authentication, cleanup
and lifetime reconnect budget through a private authenticated-session hook. The
base WebSocket public API and REQ-026 transport-only monitor keep their behavior.
Each socket sends one state_changed subscription and requires its matching
successful result before readiness. Events are validated and delivered serially
with backpressure and a delivery timeout. Rejection, protocol faults and consumer
failure have finite explicit subscription health; no event/peer error text enters
public diagnostics. Close freezes readiness before draining socket/delivery,
including a late failed consumer. Joining close from inside the consumer rejects
explicitly to prevent a self-join deadlock.

No canonical normalization, reconciliation, history/replay, exactly-once effects,
private HA certification, physical devices, BUG-033 portability repair or
Feature/Stage acceptance is supplied. A trusted consumer must cooperate with
cancellation and avoid blocking the event loop; cancellation cannot undo effects.

## Source-specific local evidence

Implementation/test/CI/artifact source:
`4bfb0664484dbd47ecacbc999fa7173c5c000962`.
Actual local environment: Linux aarch64 / CPython 3.12.12. The complete required
suites ran against identical implementation/test bytes committed at that source;
the builder then ran from a clean checkout (`source_dirty:false`). Later commits
add the planning fixture correction, delivery evidence and PR linkage only.
The new fixture correction is verified separately; it does not change runtime,
fabric tests or built package bytes.

- Required fabric suite, all eight runtime flags: **870 passed**, zero
  failures/errors/skips; required shared-contract suite: **1795 passed**, zero
  failures/errors/skips. The preceding intermediate 868-case run is superseded
  by this final source's 870-case run.
- Proposed TC-027-01/02/03/04/05 groups: **18 / 33 / 12 / 3 / 7** executed.
- Ruff and strict mypy pass. ADR/layout/agents/secrets/planning/CI-wiring,
  public-data, legacy-requirements and RLS validation pass. The planning unittest
  suite initially failed because its explicit fixture copy list omitted REQ-027;
  adding that fixture repairs the omission, with **21 tests passing**. The first
  source CI governance failure records this same omission, not a runtime failure.
- Six mutations detected with pytest exit 1: premature readiness before ACK,
  accept wrong command ID, lose explicit subscription rejection, allow closed
  health to change after a late consumer failure, reset lifetime retry budget,
  and remove the delivery deadline. Each uses a separate temporary runtime tree;
  no subprocess timeout or skip is counted as detection. Provenance stores
  selection, mutated-file hash and failure-log digest for every probe.
- Eight freshly acquired dependency wheels match exact official PyPI release
  digests before installation. Config/cache/proxy overrides are disabled by the
  existing acquisition policy. The initial sandboxed acquisition failed; the
  successful authorized run used a new output directory and fresh wheelhouse.
- Both direct and sdist-derived package pairs build, install into fresh venvs and
  pass all retained provider/demo/conformance/configuration/REST/WebSocket/health
  checks. Both additionally pass subscription smoke under **-I and -O -I** outside
  the checkout. Each subscription smoke records three connections/subscription
  commands, two ordered delivered events and zero active connections after close;
  ACK gating, reconnect, rejection, redaction, serialization and drain are checked.

[Machine-readable provenance](REQ-027-artifact-provenance.json) preserves exact
source/runtime/artifact/dependency/JUnit digests, local environment, per-TC counts,
installed distributions, all smoke reports and mutation probes. These checks are
local generator verification, not independent evaluator signatures.

## Review handoff

Remain `req_impl / generator-001`, review_round 0, unchecked AC1–AC5 and implemented
TC-027-01–05. The user will arrange external review. Do not mark ready, sign
T03/T07/T10/T13, accept ACs or merge from generator tests/CI results. No next Story
is admitted by this implementation. Final-head CI is linked in the PR and must
be read separately from historical source-specific local evidence.
