# REQ-025 local pre-review findings — remediation

[human-001][2026-10-16] Supplied the local pre-review of draft PR #53 at
`8f10602` and instructed “Fix all findings”. That report is not an independent
T03/T07/T10/T13 signature. [generator-001] implements the following repairs;
REQ-025 stays req_impl / generator-001, AC1–AC4 unchecked and TC-025-01–03
implemented. PR #53 remains draft pending external review and human acceptance.

| Finding | Disposition and falsifier |
| --- | --- |
| N1 | Response fixture now returns valid JSON describing the exact fixture wheel, digest and official URL. The identical response succeeds at the requested URL and raises precisely dependency_metadata_redirect at the redirected URL. Removing only the redirect check now fails the actual test, rather than being masked by JSON parsing. New cases reject absent/duplicate/oversized wheel METADATA and missing Name/Version before network access. |
| N2 | Pip downloads discard case-insensitive PIP_* and *_PROXY keys (including NO_PROXY), retain disabled config/cache and explicit official index. Release metadata uses build_opener(ProxyHandler({})). Hermetic hostile-proxy fixtures exercise both policies; removing either fails its real test. Provenance records disabled proxy policy and ignored key names without values. Direct official-host access is now required. |
| N3 | Every supplied JUnit report requires one positive exact expected count. Missing/extra/nonpositive baselines fail; both truncated and excess passing testcase totals fail. CI pins the revised fabric baseline to 730; the local shared baseline is 1795. These expectations are supplied independently of the parsed report; update them explicitly when the suite changes. Removing the count guard fails both under/over-count cases. |
| N4 | No Termux builder execution is inferred. A fresh Linux direct/sdist-derived build, isolated venv installation and complete installed smokes passed as recorded below. The user's Termux ensurepip/tool limitations, and BUG-033's unresolved Windows scope, remain attributed boundaries. |

The verifier consumes wheel METADATA and official release JSON. It does not read
simple-index data-dist-info-metadata, an optional metadata optimization; missing
that attribute is not an error in this verification path. Actual missing wheel
metadata and missing identity fields now have explicit negative fixtures.

## Execution and evidence

Implementation source: `8eae229a22235949bfe44ed0e242621798196c1a`.
Local platform: Linux aarch64, CPython 3.12.12. The full source suites ran against
the exact implementation bytes committed at this source; only REQ/TC prose was
added before committing. The builder then ran from that clean committed checkout.

- Required fabric: **730 passed**, zero failures/errors/skips.
- Required shared contracts: **1795 passed**, zero failures/errors/skips.
- Hermetic provenance checks: **31 passed** (included in fabric).
- TC-025-01/02/03 counts: **3 / 31 / 11**; groups overlap and are not summed.
- Governance, Fabric CI wiring, **21 planning tests**, Ruff and strict mypy pass;
  public fixtures and legacy requirements validation pass.
- Four in-memory mutations (redirect guard, pip proxy filtering, metadata proxy
  exclusion, JUnit count guard) each return pytest exit 1 in a separate process.
  None reaches the 15-second outer timeout; tracked files are never mutated.
- Official direct downloads pass: **eight** wheels verify against exact official
  release filenames/digests. Both direct and sdist-derived wheel pairs build,
  install in fresh venvs and pass all provider/demo/conformance/configuration/
  REST/WebSocket smokes, including four lifecycle smokes across -I and -O -I.
  Each lifecycle smoke observes **121** roots and four authentication attempts.
- Runtime SHA256 remains
  `f23f6600190c362e795039fa8d15f628781ddc1581778ebc12628259e7d092f5`,
  equal to accepted main and both newly built fabric wheel payloads.

[Fresh machine-readable evidence](REQ-025-review-provenance.json) contains the
actual builder report, clean source identity, source/runtime/artifact/dependency
hashes, expected and actual JUnit counts, TC grouping, installed results and
mutation outcomes/log digests. All older provenance files remain byte-identical;
this new execution does not recertify earlier artifacts or historical runs.

Commands (Python is /tmp/req019-env/bin/python):

```text
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime --require-conformance-runtime --require-ha-configuration-runtime --require-ha-rest-runtime --require-ha-websocket-runtime -q --junitxml=/tmp/req025-review-fabric.xml
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime --require-binding-runtime --require-state-runtime --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q --junitxml=/tmp/req025-review-shared.xml
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req025-review-artifacts --test-results /tmp/req025-review-fabric.xml --expected-test-count 730 --test-results /tmp/req025-review-shared.xml --expected-test-count 1795
bash scripts/check.sh
ruff check toolsets/iot/home-device-fabric
mypy --config-file toolsets/iot/home-device-fabric/pyproject.toml toolsets/iot/home-device-fabric/src
python tools/check_home_intelligence_requirements.py
python tools/check_home_intelligence_public_data.py
```

Fabric loopback tests and the networked builder run outside the restricted
sandbox with authorization. Disabling environment proxies does not establish
live HA/WSS, Windows or Termux certification. No independent acceptance,
readiness, merge, Feature or Stage completion is asserted.
