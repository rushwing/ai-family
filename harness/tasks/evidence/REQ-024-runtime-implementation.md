# REQ-024 implementation evidence

**Windows 3.13.2 scope:** the reviewed environment has four pre-existing full-suite failures
(three REST timing/socket cases and one inventory os.geteuid case). The supplied
re-review reproduced them at base f2e201b. Linux suite totals and targeted Windows
WebSocket passes do not claim a green full Windows regression suite.

**Optimization scope:** pytest counts are unoptimized acceptance runs. Pytest
under python -O strips assertions and is not evidence of behavioral correctness.
Only explicit-require() installed smoke programs supply -O -I coverage.

## Source and authority

Runtime, proposed tests, CI and artifact-builder source:
`2d1f887ea2a4132d426fc54181ee6b113525359e` on
`codex/req024-ha-websocket`, based on main `f2e201b`.
Draft [PR #51](https://github.com/rushwing/ai-family/pull/51) targets main.
Later delivery metadata does not alter this runtime/test source.

[REQ-024](../features/REQ-024.md) records human-001's combined-delivery authority
and external-review stop. This session acted as generator-001; all eight ACs
remain unchecked and all six TCs implemented. Local execution and CI are
execution evidence, not independent acceptance or authorization to advance
beyond req_impl. No reviewer messages were sent.

## Delivered behavior

The packaged `home_device_fabric.ha_websocket` module exposes a single-use
asyncio lifecycle and immutable current health. It authenticates in HA wire
order, bounds connection/authentication, applies a lifetime-wide finite retry
budget, stops on auth/protocol failure, and drains guarded cleanup on shutdown
and caller cancellation. Aclose admission closes before its first await;
cancelling a close waiter leaves owned cleanup running. No subscription,
canonical State mutation or device-command API is added.

Transport verification disables ambient proxies, redirects, compression and
credential-bearing dependency logs. WSS uses an explicit certifi CA bundle
with hostname/certificate checks. The original source's compiled OpenSSL CA
paths were absent on the standalone Linux Python; final source fixes that
portability failure without enabling ambient trust overrides. Final real TLS
tests reject a self-signed peer even when SSL_CERT_FILE points at its certificate.

## Executed verification

Linux x86_64, WSL Ubuntu 22.04, CPython 3.12.12:

| Check | Result |
|---|---|
| Full fabric, all six required-runtime flags | 689 passed; zero failures/errors/skips |
| Shared contracts, all six required-runtime flags | 1795 passed; zero failures/errors/skips |
| Planning regression suite | 21 passed |
| Ruff (fabric runtime/tests/artifact builder) | passed |
| Strict mypy (all 11 fabric source modules) | passed |
| Direct and sdist-derived compatible wheel pairs | all installed smokes passed |
| REQ-024 installed lifecycle profile | four runs: two package pairs, each -I and -O -I |

Windows x86_64 CPython 3.13.2: final source passes 53 WebSocket tests, zero
failures/errors/skips. Before the CA correction, the committed WebSocket plus
all gate tests passed 85 cases; the gate source did not change in the correction.
Final required Linux execution above covers all gate tests again.

The installed lifecycle profile independently observes four authenticated wire
exchanges per run: one connected shutdown, one terminal rejected authentication,
and two finite-retry disconnect attempts. Explicit checks survive Python -O.
Fresh environments install both compatible packages plus a recorded HTTPX,
WebSocket and CA dependency wheelhouse offline, run pip check, and execute
outside the checkout. The builder also retains all earlier installed
provider/demo/conformance/configuration/REST checks.

[Machine provenance](REQ-024-artifact-provenance.json) includes interpreter,
source commit, wheel/sdist/dependency SHA256 hashes, installed package inventory,
smoke outputs, JUnit-derived test totals, proposed TC group counts and CI snapshot.
The original builder report is augmented with source-validation metadata;
its artifact/dependency identities and smoke results are preserved.

Commands from repository root (Python is the configured test interpreter):

```bash
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini \
  toolsets/iot/home-device-fabric/tests --require-provider-runtime \
  --require-demo-runtime --require-conformance-runtime \
  --require-ha-configuration-runtime --require-ha-rest-runtime \
  --require-ha-websocket-runtime -q
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime \
  --require-action-runtime -q
python toolsets/iot/home-device-fabric/tests/build_artifacts.py \
  --out-dir /absolute/path/outside/checkout
python -m unittest discover -s tests -p test_home_intelligence_planning.py
```

## CI and governance

[Exact-source run 38567732804](https://github.com/rushwing/ai-family/actions/runs/38567732804)
passes all 11 applicable jobs: governance, changes, PG/Redis integration,
MCP, Goal lint, and both shared/fabric matrices on Python 3.12/3.13/3.14.
Fabric CI includes full required tests, lint, strict typing and installed paired
artifact verification. Frontend and legacy workbook jobs are unrelated and
path-filtered; the legacy workbook checker was also executed locally and passed.
ADR, layout, agent registry, tracked-secret scan, migration RLS, public-data,
planning integrity and legacy requirements validators pass. The planning test
fixture includes the newly admitted requirement.

## Limits and external review

No real HA account, private endpoint/token, household inventory or physical
device was used. Full Windows regression is not certified: earlier full runs
exposed existing REST timing/Proactor socket-count assumptions, os.geteuid use,
and a planning negative-test short-path alias issue. They are not silently
skipped or marked passed. The supported Linux suites above pass without skips.
Initial sandbox temp-directory and Windows event-loop failures were environment
restrictions; successful verification used normal process/loopback access.

External reviewers should derive TC expectations independently and examine
authentication ordering, finite retry semantics, cancellation/cleanup ownership,
deadline priority, supported diagnostics, logger isolation, TLS/redirect handling
and installed dependency bounds. Proposed TC text/code is generator-authored,
not a substitute for external review. Durable state, event subscriptions,
combined integration health, physical actions and Feature/Stage acceptance retain
their separate admission and acceptance gates.
