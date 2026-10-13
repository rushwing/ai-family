# Home Device Fabric

`ai-family-home-device-fabric` provides the REQ-019 typed provider protocol and
deterministic offline mock. Shared serialized records and canonical validators
live in `ai-family-state-schema`; this distribution depends on that package.

```bash
python -m pip install -e 'libs/state-schema[test]' -e 'toolsets/iot/home-device-fabric[test]'
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini \
  toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime --require-conformance-runtime -q
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/provider-artifacts
```

Import `ProviderProtocol`, `MockProvider` and `Delivery` from `home_device_fabric`.
Import `MockConfiguration`, `DeviceRegistration`, `NormalizedInput`,
`ProviderOutcome` and `ProviderError` from `state_schema.provider_contracts`.
The exact configuration, envelopes and signatures are documented in the
[API contract](../../../harness/tasks/evidence/REQ-019-api-contract.md).

Construct `MockProvider` with an explicit versioned configuration containing
inventory, separate mock bindings, capability catalogue, supported device
registrations and attempt scripts. `discover()` and `snapshot()` return immutable
records with detached JSON serialization. Initial observations are absent and
availability is unknown. Each script explicitly supplies future inputs or ACK/
failure outcomes; the mock never derives reported values from action arguments.

The caller creates and transitions a Task to `running` through the shared Action
helpers, then calls `submit(task, binding=selected_binding, attempt_id=attempt)`.
Submission validates the complete script before recording any dispatch. Consume
`advance(now_ms)` synchronously: apply each normalized input through the shared
State helpers and adjudicate correlated completion through Action Result/Task
helpers before requesting the next delivery. Call `settle(terminal_task)` when
the caller reaches a terminal state. ACK alone leaves convergence Tasks running.
The installed [smoke](tests/artifact_smoke.py) demonstrates this integration.

Virtual milliseconds are strict nonnegative integers. Deadlines win ties with
deliveries; earlier evidence can win even when advancement jumps past the
deadline. Exhausting the iterator finishes the clock at the requested time;
closing it early preserves remaining deliveries. Settlement is allowed between
yields, while submission and nested advancement reject. Cancellation suppresses
pending correlated action inputs/outcomes and keeps independent observations.
Late observations remain deliverable after timeout but cannot change terminal
Tasks. Logs and attempt tracking are per-instance test instrumentation.

This is an internal simulator with no network, wall clock, random inputs or
ambient configuration. The caller owns shared State, Task adjudication, replay
classification and explicit retries. Production authorization, confirmation,
audit, queues, adapters and durable deduplication require later admitted work.
Required-mode tests reject skips; artifact verification builds both wheel/sdist
pairs, installs them without dependencies into fresh environments and executes
`python -I` outside the checkout. Artifact hashes and interpreter provenance are
written to `provenance.json`.

Distribute compatible wheels for both packages together, or publish both to a
configured private index. The package declarations do not assume either package
is publicly indexed. For local wheel pairs, supply both wheel paths to pip; the
artifact smoke uses `--no-index --no-deps` after explicitly selecting both wheels.

## Offline device CLI

After installing a compatible pair, run these commands from any directory:

```bash
python -m home_device_fabric.demo --device switch --scenario success
python -m home_device_fabric.demo --device curtain --scenario success
python -m home_device_fabric.demo --device temperature --scenario observe
python -m home_device_fabric.demo --device switch --scenario timeout
python -m home_device_fabric.demo --device switch --scenario offline
python -m home_device_fabric.demo --device curtain --scenario invalid-position
python -m home_device_fabric.demo --device temperature --scenario write-rejected
```

Each command prints one canonical version-1 JSON object with discovery and exact
revision-1 descriptors, explicit units, per-case initial/ready/final State,
chronological timeline, Task/result or typed rejection, and dispatch count. Switch
success covers on/off; curtain success covers 0/100/40 with scripted intermediate
observations. Temperature observes 0, -5.5 and 21.25 degrees Celsius with no Task.
All IDs, report values and timestamps are fixed fictional fixtures. Virtual time
advances without sleep, services, credentials, network or environment setup.

Exit 0 means the named scenario verified its declared expectations. A timeout or
rejected write therefore exits 0 when that expected outcome is demonstrated; it
does not mean the action succeeded. Exit 1 means execution/expectation failure.
Exit 2 means unsupported arguments or device/scenario selection. Failure
diagnostics on stderr never echo argument values. Checks also run under `-O`.

For example, these are JSON projections from complete switch-success and
switch-timeout envelopes (the command itself emits the full evidence):

```json
{"device":"switch","scenario":"success","dispatch_count":2,"task_states":["succeeded","succeeded"]}
{"device":"switch","scenario":"timeout","dispatch_count":1,"task_states":["timed_out"]}
```

A small assertion users can run without pytest:

```bash
python -m home_device_fabric.demo --device switch --scenario timeout > demo.json
python -c 'import json; d=json.load(open("demo.json")); c=d["cases"][0]; assert d["simulation"] is True and d["dispatch_count"] == 1 and c["task"]["state"] == "timed_out" and c["result"]["physical_outcome"] == "unverified"; print("expected simulated timeout verified")'
```

Switch/curtain also support `mismatch`, `stale`, `wrong-epoch`, `deadline-tie`,
`late` and `timeout`; switch supports `malformed`. All three devices support
`offline`, covering both unknown and known last values. An already-offline
action rejects before dispatch in the demo caller; the provider submit contract
is unchanged. Timeout wins exact ties; late reports can update State while the
Task remains timed out. Every successful action dispatches once. Reports never
derive from submitted arguments.

`MockSwitch`, `MockCurtain`, `MockTemperatureSensor`, `configuration()` and
`build_scenario()` live in `home_device_fabric.scenarios`. Each model provides
`registration()` and `build(scenario)`. `run_demo()` / `execute_case()` live in
`home_device_fabric.caller`. Packaged scenario fixtures are the sole demo stimulus
source; tests independently specify expected values. Caller-fed initial/sensor
inputs are validated through the shared normalized-input and State helpers;
dispatched action deliveries use the existing MockProvider scheduler. The caller
owns the State projection and adjudication. Timeline records are caller JSON
records, not REQ-016 events or provider event-channel publications.

The [demo API contract](../../../harness/tasks/evidence/REQ-020-api-contract.md)
freezes the envelope and error vocabulary. Compare complete stdout text,
serialized with sorted keys, compact separators and finite values, including
the final newline. This preserves booleans/numeric types and list order. The
paired-artifact verifier runs all seven commands, repeat and optimized runs with
`python -I -m home_device_fabric.demo` outside the checkout on both direct-built
and sdist-derived compatible wheel pairs, and records artifact/interpreter
provenance. Select both wheel paths and install with `--no-index --no-deps`;
alternatively publish both distributions to a configured private index.

For action cases the caller constructs a provider for the unknown initial snapshot,
then constructs its dispatch provider after the complete attempt script is known:
REQ-019 freezes scripts at construction. Caller State retains the admitted initial
observations; the dispatch provider's own snapshots start unknown. The CLI's
`capabilities` list selects the exact supported ID and revision and preserves the
canonical descriptors, including empty `events`. `write_temperature` is a
deliberately nonexistent action used only by the sensor write-rejection fixture;
the temperature capability defines no action.

CLI internal failures use fixed value-free diagnostics. For debugging, call
`run_demo("switch", "success")` or `execute_case(case)` directly from Python;
exceptions propagate with their tracebacks through those library APIs.
`scenarios.py` is the CLI's authoritative fixture source; `tests/fixtures.py`
serves only REQ-019 provider contract tests. The autouse test guard covers
network/process/clock/random access. A separate test denies file/environment/
datetime access after explicitly loading the fixed packaged catalogue. Gate
self-tests create their own present/absent import stubs and run even when the
runtime is missing; required acceptance flags still fail missing code or skips.

On platforms such as Termux, use a writable canonical `TMPDIR` (resolve symlink
aliases) for redirects, temporary directories and `--out-dir`, rather than assuming
`/tmp` is writable. The build verifier uses `venv` with `ensurepip`; platforms
without it can use an equivalent `virtualenv`, install both wheel paths with
`--no-index --no-deps`, then run `python -I` with `tests/demo_artifact_smoke.py`
outside the checkout. This portability procedure does not replace the documented
Python 3.12/3.13/3.14 CI build and smoke checks.


## Reusable offline conformance

```bash
python -I -m home_device_fabric.conformance > conformance.json
python -c 'import json; from home_device_fabric.conformance import validate_report; raise SystemExit(0 if validate_report(json.load(open("conformance.json"))) else 1)'
```

The conformance runner executes 51 fixed checks of the fictional offline profile,
with independently declared observations and expected values. It does not import
`demo.py` or `caller.py`, and never treats the demo's verdict as an oracle. The
human-oriented demo shows a selected scenario; conformance checks cover the full
reviewed inventory and can observe a supplied provider through public contracts.

Each command emits one sorted compact version-1 JSON report plus newline. Exit 0
means every mandatory check passed, including expected device timeout/rejection
cases; 1 means a check, setup or inventory failed; 2 means invalid arguments, with
fixed `invalid_arguments` stderr. `--help` displays usage. Checks survive `-O`.
The report contains `profile`, `inventory_version`, `inventory_sha256`, the complete
`expected_cases`, per-case `executed/status/evidence/error`, strict counts and
`passed`. Inspect actual evidence, not only the overall verdict. `validate_report`
checks the trusted ordered inventory, report structure/counts and finite JSON;
it returns true only for complete passing reports. The pinned hash detects
inventory drift/truncation against this trusted package. It is not a signature
and does not authenticate evidence or protect against replacing the verifier.

```python
from home_device_fabric import MockProvider
from home_device_fabric.conformance import ConformanceDriver, run_conformance, validate_report

def provider_factory(configuration_data):
    return ConformanceDriver(MockProvider(configuration_data))

report = run_conformance(provider_factory)
if not validate_report(report):
    raise RuntimeError("offline conformance failed")
```

The factory receives detached validated configuration with explicit scripts
before constructing its provider. Return a `ConformanceDriver` whose `provider`
satisfies the full existing `ProviderProtocol`. `advance(now_ms)` delegates to
that provider's virtual-time method. Custom forwarding providers and driver
subclasses can be supplied; `dispatch(task, *, binding, attempt_id, verdict)` is
the caller-policy seam and suppresses replay/conflict/offline/invalid verdicts.
Provider-negative submissions bypass caller policy deliberately. Factories must
create fresh context and expose detached public records. Future live adapters
need separate reviewed drivers/applicability mappings; these checks do not
certify hardware, production authorization or durable deduplication.

Library failures are reported per case with fixed value-free codes: setup_failed,
check_failed, identity_mismatch, catalogue_mismatch, invalid_dispatch,
state_mismatch, completion_mismatch, delivery_mismatch, rejection_mismatch and
policy_mismatch. The runner continues to account for the remaining inventory.
Initial/sensor observations are caller inputs; action deliveries use the supplied
provider. Shared validators adjudicate State, Tasks, evidence and replay, while
independent expected values/times/counts verify their effects. A fixed catalogue
expectation snapshot is version-controlled; it is never obtained from the live
catalogue as its own oracle. The only runtime file loading is the declared shared
packaged initial catalogue; no ambient configuration or wall clock is used.

`--require-conformance-runtime` rejects absent conformance/shared components,
mandatory runtime inventory failures and skipped acceptance. The session gate
executes and validates the full packaged inventory even when pytest selection
omits conformance TCs. Required acceptance still includes the complete suite.
Hermetic probes block ambient-install fallback. Independent wrappers exercise
identity/support, fake ACK/mismatched report, timeout-tie, duplicate-delivery and
caller replay defects. Installed smoke additionally runs a forwarding wrapper
and detects a defective identity wrapper outside the checkout with `-I` and `-O`.
Compatible direct/sdist-derived wheel pairs are installed together using
`--no-index --no-deps`; provenance records hashes, interpreters, case counts,
report hash and installed defect detection. See the
[proposed API/TC contract](../../../harness/tasks/evidence/REQ-021-api-contract.md).
This delivery remains req_impl pending external review and acceptance.
