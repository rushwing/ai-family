# Home Device Fabric

`ai-family-home-device-fabric` provides the REQ-019 typed provider protocol and
deterministic offline mock. Shared serialized records and canonical validators
live in `ai-family-state-schema`; this distribution depends on that package.

```bash
python -m pip install -e 'libs/state-schema[test]' -e 'toolsets/iot/home-device-fabric[test]'
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini \
  toolsets/iot/home-device-fabric/tests --require-provider-runtime -q
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
