# REQ-019 Runtime Implementation Evidence

Human-001 authorized combined TC design/code/runtime delivery after merging PR #38,
with external review deferred until implementation completion. This is generator-001
self-check evidence. Independent T03/T07/T10/T13 acceptance remains pending;
AC1–AC8 remain unchecked, and TC-019-01–06 are implemented.

## Runtime and verification

Shared records live in `state_schema.provider_contracts`. The separately packaged
`home_device_fabric` supplies the runtime-checkable protocol, immutable Delivery
and synchronous MockProvider. Admission checks canonical bindings, exact supported
revisions, property ownership and complete scripts before any dispatch effect.
Explicit observations use actual Capability/State validators; callers use actual
Action Result/Task helpers and settle terminal Tasks between iterator yields.
Deadlines precede same-time evidence, while earlier evidence can complete across
a large time jump. Cancellation keeps independent observations; timeout retains
late observations without changing terminal Tasks. No implicit observation,
automatic retry, shared-store write or production authorization is introduced.

Linux aarch64 local verification uses CPython 3.12.12, 3.13.5 and 3.14.3.
On **each interpreter**, all 108 provider tests and 1,795 prior shared-contract
tests pass, with zero failures or skips. Required-mode gate probes demonstrate
optional absence skips, required absence exit 4 and required explicit skip exit 1.
The three subprocess probes deliberately restore process creation and sleep only
while launching pytest; provider calls remain under counted ambient-effect denial.
The initial continuation found 97 passing cases and three invalid fictional event
fixtures, fixed by adding Event metadata and the accepted `additionalProperties`
schema key. Additional coverage validates discovery roundtrip, legitimate integer
zero/read-only support and malformed inputs.

| TC | Cases passed per interpreter | Failed/skipped |
|---|---:|---:|
| TC-019-01 | 33 | 0/0 |
| TC-019-02 | 20 | 0/0 |
| TC-019-03 | 19 | 0/0 |
| TC-019-04 | 13 | 0/0 |
| TC-019-05 | 3 | 0/0 |
| TC-019-06 | 20 | 0/0 |

Registered `tc019_01`–`tc019_06` pytest markers identify the counts.
JUnit outputs: `/tmp/req019-provider312.xml`, `provider313.xml`, `provider314.xml`
(each with the `/tmp/req019-` prefix), plus `/tmp/req019-shared312.xml`,
`shared313.xml`, `shared314.xml` under the same prefix.
The inherited handoff records 86 optional absent-runtime cases before runtime;
that historical count is retained, not re-attributed to this continuation.

```bash
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini \
  toolsets/iot/home-device-fabric/tests --require-provider-runtime -q
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests \
  --require-inventory-runtime --require-binding-runtime --require-state-runtime \
  --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q
ruff check libs/state-schema/src libs/state-schema/tests toolsets/iot/home-device-fabric
mypy --config-file libs/state-schema/pyproject.toml libs/state-schema/src
mypy --config-file toolsets/iot/home-device-fabric/pyproject.toml toolsets/iot/home-device-fabric/src
bash scripts/check.sh
python3 tools/check_home_intelligence_public_data.py
python3 tools/check_home_intelligence_requirements.py
git diff --check
```

Lint and strict typing pass (eight shared source modules, two fabric modules).
Governance, 21 planning regressions, public-data and legacy requirement checks pass.
Runtime tests count denied common network/process/clock/random/environment accesses,
including swallowed failures. An explicit integration test also denies file reads
and datetime/environment lookups after fixture creation. These are Python guards,
not a native-code security sandbox.

## Installed artifacts and CI

`python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/provider-artifacts`
builds direct wheels and sdists of both distributions, extracts each sdist using
the stdlib data filter, and builds derived wheels without build isolation or
dependency downloads. Each wheel pair installs with `--no-index --no-deps` into
a fresh venv; `python -I` executes the smoke outside the checkout and asserts
runtime imports come from that environment. Only explicit fictional fixtures are
read from the checkout, without injecting source paths. Each pair confirms
discovery, ACK remaining running, an independently scripted false observation,
real shared-helper completion and suppression of further deadlines/delivery.
Both pairs pass locally on all three interpreters.

Artifact/interpreter provenance is emitted as `provenance.json`; direct and derived
wheels are byte-identical for each distribution. Final artifact hashes and source
commit are recorded below after committing the tested implementation.

Blocking CI job `home-device-fabric-tc` covers Python 3.12/3.13/3.14, lint/type,
zero-skip required TCs and paired artifact verification. Its path filter covers
shared contracts, fabric and CI changes. The existing shared job, six required
flags and installed shared-only wheel smoke remain intact. CI uploads JUnit,
both wheel pairs, sdists and interpreter/hash provenance per matrix member.

External combined review of TC text/code and runtime remains pending. The draft
implementation PR will supply CI traceability; no readiness or merge is authorized.
