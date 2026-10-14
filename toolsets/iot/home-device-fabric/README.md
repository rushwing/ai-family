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

Install both packages into the interpreter used for pytest before running the
suite. CLI subprocess tests use `python -I`, which ignores `PYTHONPATH`; setting
`PYTHONPATH` alone cannot make the packages available to those subprocesses.
Use the editable installs above or install both compatible wheels together.

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
before constructing its provider. The factory must return a `ConformanceDriver`
instance or subclass instance. The wrapped `provider` implements the full
existing `ProviderProtocol`; returning that provider alone produces
`setup_failed`. Subclass `ConformanceDriver` to override caller policy while
keeping the provider wrapped. `advance(now_ms)` delegates to
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
policy_mismatch. `setup_failed` identifies factory construction or driver/provider
type failures. `check_failed` identifies an unexpected exception during a check
or an evidence sanitization failure. Invalid or non-finite evidence becomes
`{"diagnostic":"invalid_evidence"}` with `check_failed` and failed status so the
report remains finite JSON. Diagnostics omit exception messages/chains; ordinary
evidence still contains the observable fictional values. Detailed fixed-code
meanings are in the [API contract](../../../harness/tasks/evidence/REQ-021-api-contract.md).
The runner continues to account for the remaining inventory.
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
Human final acceptance and PR #43 merge are recorded in the
[closeout evidence](../../../harness/tasks/evidence/REQ-021-review-acceptance.md).
Feature/Stage completion and future live-profile acceptance remain separate.

## Offline Home Assistant configuration (REQ-022)

This adapter-local module validates explicit inputs without contacting HA or
loading environment/files. Validation proves syntax and bounds, not connectivity,
authentication, TLS policy or endpoint safety. Existing provider/mock contracts
and top-level exports are unchanged. Credential acquisition is a separately
reviewed future increment.

```python
from home_device_fabric.ha_configuration import HAConfiguration

configuration = HAConfiguration(
    {"schema_version": 1, "base_url": "HTTPS://EXAMPLE.INVALID:443/"},
    access_token="fictional-example-token",
)
print(configuration.to_redacted_json())
print(configuration.reconnect_delays_ms())
# Trusted future transport composition only; do not log these connection inputs:
endpoint = configuration.base_url
credential = configuration.access_token_for_transport()
```

Use `to_redacted_dict()` or `to_redacted_json()` for diagnostics. Trusted
transport composition uses `base_url` and `access_token_for_transport()`; these
return the normalized endpoint and original credential, so do not log them.

Settings must be a plain dict with plain string keys. schema_version is strict
integer 1 and base_url is required. Unknown keys (including access_token inside
settings), missing fields and primitive/container subclasses reject. Optional
fields default only when omitted; null/bool/float/string never coerce.

| Setting | Inclusive strict integer range | Default (milliseconds except attempts) |
|---|---|---|
| request_timeout_ms | 1–120000 | 10000 |
| reconnect_initial_delay_ms | 1–60000 | 1000 |
| reconnect_max_delay_ms | 1–300000 and >= initial | 30000 |
| reconnect_max_attempts | 1–32 | 8 |

base_url is at most 2048 characters: absolute ASCII http/https root, ASCII DNS
labels (1–63 characters, letters/digits/internal hyphens, total <=253, no trailing
dot), strict dotted IPv4 or bracketed IPv6 (no zones). Single-label DNS works;
legacy numeric/hexadecimal IP spellings reject. Ports are 1–65535 decimal digits;
explicit spellings remain, including :80, :443 and :00443. Scheme/host lowercase;
one trailing slash is removed. Userinfo, query/fragment even empty, non-root paths,
percent-encoded authority, non-ASCII hosts, whitespace/control characters,
backslashes and malformed authority reject. No DNS, host classification or
reverse-proxy prefix support is implied.

Preserving explicit port spelling means equivalent endpoints such as
`https://h.invalid:443` and `https://h.invalid:00443` have different stored strings.
The configuration has no endpoint-equivalence comparison or deduplication API;
future transport code must define its own reviewed comparison policy.

The separate token is a plain str of 1–8192 printable ASCII characters without
whitespace. No trim, JWT decoding, authenticity inference or fallback. The object
is immutable and detached from inputs. reconnect_delays_ms() returns a finite
immutable tuple: zero-based i uses min(initial*2**i, max), initial connection is
outside the reconnect budget. Default: (1000, 2000, 4000, 8000, 16000, 30000,
30000, 30000). attempts=1 returns (initial,). Repeated inspection is stable;
there is no connection state, retry execution, sleep, jitter or automatic reset.

Exact redacted snapshot fields: schema_version=1, base_url="<redacted-endpoint>",
access_token="<redacted>", and the four numeric settings above. No endpoint
scheme/host or credential prefix/suffix/hash/length is included. to_redacted_dict()
returns a fresh mapping; to_redacted_json() gives sorted compact JSON. repr/str
and container repr use redacted diagnostics. vars/dataclasses.asdict/default
json.dumps refuse the non-dataclass slots object; pickle/copy serialization also
refuses, including direct __getstate__/__reduce__. There is no raw dictionary export. Deliberate base_url and
access_token_for_transport() expose actual connection inputs to trusted library
callers. Slots/private names are not protection against explicit private
introspection, debugger/process-memory access or caller-source disclosure.

HAConfigurationError (ValueError) carries fixed code and tuple path; its message
is code + ': ' + dot-joined path. Unknown keys use settings.<unknown>. Key scans
follow dict insertion order, but all unknown keys produce the same fixed error;
reordering them does not change the visible diagnostic. Required fields and
numeric settings are checked in the fixed order documented in the API contract.
Submitted values and parser exception messages/chains are omitted. Codes: invalid_settings,
unknown_field, missing_field, invalid_setting, unsupported_version, out_of_bounds,
invalid_endpoint, missing_token, invalid_token and invalid_reconnect_order.
[Proposed exact API/TC contract](../../../harness/tasks/evidence/REQ-022-api-contract.md)
records meanings and error precedence. Human final acceptance and PR #46 merge
are recorded in [closeout evidence](../../../harness/tasks/evidence/REQ-022-review-acceptance.md).
This offline configuration supplies no live HA certification or transport;
Feature/Stage acceptance remains separate.

Acceptance adds --require-ha-configuration-runtime alongside the existing
--require-provider-runtime --require-demo-runtime --require-conformance-runtime.
Install compatible packages into the pytest interpreter first (editable or wheel
pairs); python -I subprocesses ignore PYTHONPATH. tests/build_artifacts.py retains
paired --no-index --no-deps direct and sdist-derived wheel installation and adds
installed configuration smoke outside the checkout, under -I and -O -I, with
explicit checks that survive optimization. Provenance records wheel/sdist hashes,
interpreter and configuration rejection/redaction/schedule results.

## Authenticated runtime information (REQ-023)

`home_device_fabric.ha_rest` supplies `HARestClient`, `HARuntimeInfo` and
`HARestError`. Install the fabric package with its HTTPX dependency
(`>=0.28.1,<0.29`). Reuse explicitly supplied `HAConfiguration`; no environment
or file credential lookup takes place. No HA account or physical device is
required for the fake-server acceptance suite.

```python
from home_device_fabric.ha_rest import HARestClient, HARestError

async def read_runtime(configuration):
    async with HARestClient(configuration) as client:
        try:
            info = await client.runtime_info(correlation_id="runtime-check-1")
            return info.to_dict()  # exactly {"version": "..."}
        except HARestError as error:
            return error.to_dict()  # code, correlation_id, http_status only
```

Each call owns one fresh transport and sends one authenticated GET to
`base_url + /api/config`. Only the validated version is returned. Redirects
(including HTTP-to-HTTPS), compressed responses, invalid JSON/media and bodies
over 256 KiB reject. Configure the final endpoint directly. TLS verification is
enabled; ambient proxies/trust overrides, retries and cookie reuse are disabled.
There are no generic request or device-write methods.

IDs are exact ASCII strings of 1–64 characters, starting with a letter/digit and
continuing with letters/digits/period/underscore/hyphen. Complete credential or
endpoint echoes reject. Error codes: `auth_failed` (401), `http_error` (other
non-200), `timeout`, `transport_failed`, `invalid_response`, `client_closed`,
`client_busy`, `invalid_correlation_id`. Arguments/messages contain only the
code; dependency exception causes/contexts are discarded. Client/result repr
is constant and client pickle/copy/raw-state exports refuse. Deliberate private
introspection, traceback-frame locals and HTTP-core DEBUG/wire tracing are
outside this diagnostic boundary; do not enable sensitive transport tracing.

The asyncio wrapper admits one active call on one event loop; a second fails
immediately. Close marks it closed and waits for the admitted operation without
cancelling it or changing its outcome. Cancellation of a close waiter does not
cancel that operation. The monotonic request budget includes transport setup,
headers and body; expiry wins over ordinary results/errors. One separate 1000 ms
cleanup guard covers both owned resource closes, with external cancellation
propagated after cleanup. Synchronous work/event-loop scheduling and resolver
workers cannot be forcibly preempted, so these are bounded asynchronous waits,
not hard real-time termination guarantees.

Add `--require-ha-rest-runtime` to the four existing fabric required flags.
REST tests permit numeric loopback sockets, event-loop clocks and TLS fixture
entropy explicitly; existing pure-runtime effect-denial remains active. Artifact
validation resolves a dependency wheelhouse once, records SHA256 hashes, then
installs each direct/sdist-derived compatible package pair and the HTTPX closure
offline into fresh environments. Independent `-I` and `-O -I` smoke scripts
exercise actual wire headers, timeout, TLS rejection and draining close.

[Proposed API/TC contract](../../../harness/tasks/evidence/REQ-023-api-contract.md)
and [implementation evidence](../../../harness/tasks/evidence/REQ-023-runtime-implementation.md)
record the review scope. Human final acceptance and PR #49 merge are recorded
in [closeout evidence](../../../harness/tasks/evidence/REQ-023-review-acceptance.md).
The bounded read-only increment is delivered; live installation acceptance remains separate.


### REST pre-review clarifications

Nonstandard HTTP statuses (for example 600/999) produce `http_error` with
`http_status=None`; standard non-success statuses retain only their 100–599
integer. Ordinary resource-close exceptions preserve a classified success or
failure. Cleanup guard expiry and the post-cleanup request deadline check still
produce `timeout`, even if the response arrived within the network budget.
Re-entering a closed async context raises `RuntimeError("client_closed")`;
`runtime_info` instead raises the correlated `HARestError("client_closed")`.
Validated runtime-info/error projections support pickle and copy round trips;
restored errors discard traceback, cause, context and notes. Client exports
remain refused.

Environment proxies are excluded structurally by constructing the transport
without proxy configuration. The observable `trust_env=False` effect is ignoring
ambient TLS trust overrides (`SSL_CERT_FILE` / `SSL_CERT_DIR`). A real failed
connection test counts one TCP connect attempt to verify zero implicit retries.

The artifact builder requires CPython's `venv` and working `ensurepip` to create
fresh pip-enabled environments. This path is validated on Linux CPython
3.12/3.13/3.14; Android/Termux builds without `ensurepip` cannot run it unchanged.
A manually created `virtualenv` can run the installed smoke scripts with the same
compatible wheel pair and dependency closure, but does not establish that the
full artifact builder/matrix ran. Record platform and setup method with results.

External reviewers must independently derive TC expectations for T07/T10 and
explicitly assess post-cleanup deadline priority. The local pre-review and its
fixes do not supply independent approval or trigger T12/T13, readiness or merge.

## WebSocket lifecycle (REQ-024, pending external review)

`home_device_fabric.ha_websocket` exposes `HAWebSocketClient` and immutable
`HAConnectionHealth`. It uses the explicit `HAConfiguration` and
`websockets>=15.0.1,<16`. Constructing a client performs no I/O. Await `run()`
in an owned task; it stays active through connections and finite retries, then
returns on terminal failure or shutdown. Inspect `health().to_dict()` for
`state`, `reason`, `reconnect_attempt` and monotonic transition `sequence`.

```python
import asyncio
from home_device_fabric.ha_websocket import HAWebSocketClient

async def observe_connection(configuration):
    client = HAWebSocketClient(configuration)
    running = asyncio.create_task(client.run())
    try:
        await running  # terminal failure; an owning application may close earlier
        return client.health().to_dict()
    finally:
        await client.aclose()
```

The client upgrades `/api/websocket`, waits for `auth_required`, sends the
explicit token and publishes connected only after `auth_ok`. Authentication
rejection and invalid protocol stop immediately. Transient loss uses the exact
configured finite reconnect tuple; successful reconnect does not reset this
lifetime budget. The current snapshot is transport health only. Subscriptions,
combined REST/WS health and device state/actions remain later increments.

One client starts once on one asyncio loop. `aclose()` closes admission, cancels
connect/auth/backoff/idle receive and drains cleanup. Concurrent/repeated close
is safe; cancelling a close waiter does not cancel owned cleanup. Cancelling
`run()` drains the worker and propagates caller cancellation. Socket close has
a separate 1000 ms cleanup guard with transport abort on failure/expiry.

Proxies, redirects, compression and dependency logs are disabled. WSS checks
hostname/certificate using the explicit certifi CA bundle without ambient TLS overrides.
The auth exchange shares `request_timeout_ms`; keepalive ping/pong use 20s/20s,
incoming messages are bounded to 64 KiB and four queued frames. No public raw
send or device-write method exists. Health and client repr contain no raw peer
text/credentials/endpoint; raw client serialization refuses. Private introspection
and explicitly instrumented process/wire tracing are outside this boundary.

Add `--require-ha-websocket-runtime` to the five existing required fabric flags.
The [requirement](../../../harness/tasks/features/REQ-024.md) holds unchecked ACs
and implemented TCs pending external review. The artifact builder executes the
installed lifecycle smoke under `-I` and `-O -I` for direct/sdist-derived package
pairs and records the WebSocket dependency closure. No live HA is required.
