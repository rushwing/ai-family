# REQ-026 / HI-S004 proposed runtime delivery

This is the original source-specific execution record. The subsequent
[local pre-review remediation](REQ-026-review-fixes.md) supersedes its active
health hash, counts and mutation coverage; the original provenance stays intact.

[human-001][2026-10-16] Authorized merging PR #53 and implementing the next
slice in another PR, stopping at req_impl for externally arranged review.
[generator-001] Delivers the recommended HI-S004 integration-health increment in
draft [PR #54](https://github.com/rushwing/ai-family/pull/54). The preceding
[REQ-025 acceptance](REQ-025-review-acceptance.md) is separately authorized;
it supplies no approval of this new implementation.

## Behavior and scope

HAHealthMonitor owns the accepted REST and WebSocket clients and reports
independent component health. REST failures do not manufacture a socket failure;
combined connected requires fresh REST success and an authenticated socket.
Sampling expires stale successful REST observations even during a pending probe.
REST probes never overlap, terminal sockets do not restart or gain new retry
budgets, and close freezes readiness before draining all owned tasks/clients.
An explicit pre-start cleanup path handles a supervisor cancelled before its
first instruction. No accepted REST/configuration/WebSocket source is changed.

The interval governs observation/probe scheduling and expiry; network detection
still includes the configured REST deadline and bounded cleanup, and scheduler
stalls are not hard real-time guarantees. Synchronous running health reads on
the owning event loop refresh expiry and socket observations without I/O.
A closed snapshot retains last component diagnostics while readiness is false/
unknown. Authenticated event_stream_connected does not certify subscriptions,
entity freshness, devices, live HA, HI-F001 or R1 completion.

## Actual source and verification

Implementation/test/CI/artifact source:
`901abd32d3622903bcc6b6dcf79218a3492aabc4`.
Actual local environment: Linux aarch64 / CPython 3.12.12. Source suites ran
against the same implementation bytes subsequently committed at this source;
planning fixture/documentation changes preceded commit. The full builder then
ran from that clean checkout. Later commits add delivery records/PR linkage only.

- Full required fabric (all seven runtime flags): **794 passed**, zero failures,
  errors or skips. This includes 57 health tests and seven new required-gate probes.
- Full required shared-contract suite: **1795 passed**, zero failures/errors/skips.
- Proposed TC-026-01/02/03/04/05 groups: **38 / 7 / 5 / 7 / 8**. Groups overlap
  (the real-composition check also belongs to installed verification); do not sum.
- Governance, complete fabric CI wiring, **21 planning tests**, Ruff and strict
  mypy pass. Public fixtures and legacy requirements validation pass.
- Five real-regression mutations fail with pytest exit 1: remove REST from
  combined readiness; remove stale-success expiry; expose socket readiness after
  close; remove unused-client cleanup for a supervisor cancelled before startup;
  use an unsafe constant correlation ID for a one-character credential.
  Separate in-memory mutation processes never change tracked files. None hits
  its 15-second outer timeout; no timeout counts as detected.
- Eight dependency wheels are downloaded with config/cache/proxy overrides
  disabled and match exact official PyPI release digests before installation.
- Both direct and sdist-derived wheel pairs build, install into fresh venvs and
  pass retained provider/demo/conformance/configuration/REST/WebSocket checks.
  Both pairs additionally pass real REST/WebSocket health composition under
  **-I and -O -I**. Each of four health smokes records three wire authentications
  and four REST requests in this execution. No short wall-clock request-count
  assumption is an acceptance condition; the smoke waits on observed states.

New health-runtime SHA256:
`a1cc336ac8e8fd9a308b7b3fa9b9be077e02134023ab5af447daadfd32154127`.
Both fabric wheel payloads match that exact module hash. Accepted WebSocket
SHA256 remains
`f23f6600190c362e795039fa8d15f628781ddc1581778ebc12628259e7d092f5`.
All 13 existing evidence JSON files, and the accepted configuration/REST/
WebSocket modules, were compared byte-for-byte to merged main and are unchanged.

[Fresh machine-readable provenance](REQ-026-artifact-provenance.json) retains
clean source identity, platform/interpreter, health/runtime and artifact hashes,
verified dependency identities, explicit expected versus actual JUnit counts,
TC groups, installed results and mutation output hashes. Earlier provenance is
preserved as evidence of its own executions.

## Commands

Python is /tmp/req019-env/bin/python:

```text
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime --require-conformance-runtime --require-ha-configuration-runtime --require-ha-rest-runtime --require-ha-websocket-runtime --require-ha-health-runtime -q --junitxml=/tmp/req026-fabric.xml
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime --require-binding-runtime --require-state-runtime --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q --junitxml=/tmp/req026-shared.xml
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req026-artifacts --test-results /tmp/req026-fabric.xml --expected-test-count 794 --test-results /tmp/req026-shared.xml --expected-test-count 1795
bash scripts/check.sh
ruff check toolsets/iot/home-device-fabric tools/check_fabric_ci.py
mypy --config-file toolsets/iot/home-device-fabric/pyproject.toml toolsets/iot/home-device-fabric/src
python tools/check_home_intelligence_public_data.py
python tools/check_home_intelligence_requirements.py
```

Loopback tests and the networked builder ran outside the restricted sandbox with
authorization. Pytest acceptance uses ordinary execution; only explicit require()
installed programs supply optimization coverage. No local Python 3.13/3.14,
Windows, Termux or live HA run is inferred. BUG-033 remains separately open.

During development a subtraction-based expiry comparison exposed float boundary
rounding; comparison now uses the absolute deadline. The controlled clock also
models zero-delay yielding correctly. The isolated planning fixture was updated
to include the new acceptance-link target. Initial failures are not reported as
passing checks; the corrected full suites/gates above actually passed.

## Review boundary

REQ-026 remains req_impl / generator-001, review_round 0, five unchecked ACs and
five implemented TCs. These are proposed generator-authored criteria and tests;
the human arranges external review. No independent T03/T07/T10/T13 signature,
req_impl_review transition, readiness, merge or Feature/Stage acceptance follows
from this implementation or successful checks.
