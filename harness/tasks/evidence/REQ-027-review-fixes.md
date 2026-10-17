# REQ-027 local pre-review remediation

[human-001][2026-10-17] Supplied a local pre-review of PR #56 at `5e77e77a`
and instructed “Fix all finding”. The report is a non-signing review input;
no T03/T07/T10/T13 approval, lifecycle transition or final acceptance is inferred.
[generator-001] implements the following disposition at repair source
`442ddc2feef3cecdca7546ce0944fdd7cd851cc4`.

## F1 — release failed readiness gates and bound the real-peer checks

The reported failure is reproduced by the premature-readiness mutation. The
smoke now releases its first peer's ACK gate in finally, before closing/joining
the client. Awaiting the run task remains in a nested finally, and the rejection
client also closes in finally. The standalone check has a 15-second outer
asyncio timeout; its pytest caller additionally uses wait_for(check(), 15).
Thus the server context can join its peer even when the readiness assertion fails.

A new real-loopback regression makes subscription_health claim readiness before
ACK, expects the original fixed RuntimeError and checks zero remaining tasks.
The entire 69-case subscription file, without -x/fail-fast, is also executed
against an isolated premature-readiness source mutation: **3 failed, 66 passed
in 0.52 seconds**, subprocess return code 1 (1.04 seconds including startup).
Standalone smoke against the same mutation exits 1 with
installed_subscription_check_failed under both -I and -O -I (0.24 / 0.31 seconds
including startup). No TimeoutError, external deadline, skip or signal is counted
as successful detection. This directly covers the formerly unbounded failure path.

## F2 — clarify consumer shutdown coordination and test the alleged child join

The direct close_from_consumer task-identity guard is unchanged. README and REQ
now explicitly say that an adapter consumer should signal a supervisor started
outside delivery and return; it must not await its shutdown indirectly through a
child task, gather or wait_for. The guard only identifies a direct reader-task
call, not arbitrary dependency graphs, and close cancels in-flight delivery.

The report's child-task deadlock was a read-code hypothesis, not a reproduction.
A bounded local probe and new named regression reproduce that precise pattern:
closing from a child cancels the reader, which cancels its awaited child close
waiter; owned closure continues and drains. No deadlock was reproduced in this
case on the tested loop. A paired regression verifies the recommended supervisor
notification pattern completes without cancelling the consumer. Both cases use
three-second waits and assert closed health, one socket close and no pending
tasks. This does not promise graceful completion for arbitrary consumer-created
dependency graphs or cancellation-resistant consumers. No timeout/abort policy
is added to the accepted production cleanup implementation.

## F3 — preserve the reviewer environment limit and supply fresh installed evidence

The supplied Termux CPython 3.14.6 report cannot run fresh-venv paired builds due
to ensurepip limits. That environment limitation requires no runtime repair and
is not claimed fixed. This remediation independently executes the complete
builder on Linux aarch64 / CPython 3.12.12 from the clean repair source. Fresh
direct and sdist-derived wheel pairs install with eight officially verified
dependency wheels and pass all retained installed checks. Four subscription
smokes (both pairs under -I and -O -I) each report three connections, two delivered
events and zero active connections after close. CI separately runs the declared
Python 3.12/3.13/3.14 package matrices; read final-head results in PR #56.

## Actual verification and source boundaries

- Complete required fabric suite: **873 passed**, zero failures/errors/skips;
  complete required shared suite: **1795 passed**, zero failures/errors/skips.
- Proposed TC-027-01/02/03/04/05 groups: **18 / 33 / 14 / 4 / 7** executed.
  test_ha_subscription.py contains **69 cases**; CI expected count is now 873.
- All original six mutation categories rerun successfully, plus the full-file
  no-fail-fast and two standalone premature-readiness probes: **nine detected**,
  no subprocess timeout counted. Logs, selections, timings and digests are in
  [fresh provenance](REQ-027-review-fixes-provenance.json).
- Ruff, strict mypy, ADR/layout/agent/secret/planning/CI-wiring/public-data/
  requirements/RLS gates and **21 planning tests** pass.
- The complete builder records source_dirty:false at repair commit 442ddc2.
  The two suites ran against identical repair bytes committed at that source.
  New provenance additionally records smoke/test SHA256 so changed verification
  bytes are distinguishable despite unchanged production runtime hashes.
- ha_subscription.py, ha_websocket.py and ha_health.py retain their original
  runtime SHA256 values (0739a731…, d8fdec51…, bfa0cdb9…). This is test/fixture,
  contract clarification, CI count and evidence remediation. Historical JSON
  evidence remains unchanged; the new record supersedes the active baseline
  without rewriting its original source-specific observations.

Remain req_impl / generator-001, review_round 0, AC1–AC5 unchecked, TC-027-01–05
implemented and PR #56 draft. The evidence/link follow-up changes no tested
runtime, subscription-test, smoke or CI bytes. External review, human acceptance,
merge, live HA and Feature/Stage completion retain their separate gates.
