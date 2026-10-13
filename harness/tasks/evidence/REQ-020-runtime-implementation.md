# REQ-020 Combined TC and Runtime Implementation Evidence

Author: generator-001 under [human combined delivery instruction](../features/REQ-020.md). This is local implementation evidence, not independent T03/T07/T10/T13 approval. Status remains req_impl / generator-001; AC1–AC8 and independent acceptance remain pending. PR #40 remains draft.

Tested source tree committed as `e54a6379844ca5556c6d22fe9bf9371cf1cbcf93` (the tests/builds ran on the identical working tree immediately before this commit). Base specification head: `443b7d416379b60a151d5ee874fcc47f930cdac2`. Platform: Linux 6.12.62+rpt-rpi-2712 aarch64. No changes to shared validators, capability descriptors or MockProvider runtime.

## Delivery

Packaged reusable switch/curtain/temperature models, explicit fixtures, caller State projection, actual shared Action adjudication, and python -m home_device_fabric.demo. Six proposed TC groups and required-demo-runtime gate; expanded existing missing-runtime subprocess probes. Offline-before-dispatch stays in caller policy. Units are demo metadata for validated exact revision-1 identities, with no descriptor field changes. Initial/sensor inputs are caller-fed validated observations; all dispatched action deliveries use MockProvider scheduling. Timeline records never enter the provider event channel.

## Executed Validation

| Interpreter | Provider/demo executed | Shared six-flag executed | Failed / skipped | Direct / sdist-derived CLI smoke |
|---|---:|---:|---|---|
| CPython 3.12.12 | 169 | 1,795 | 0 / 0 | Both pass; seven commands each, repeat + -O |
| CPython 3.13.5 | 169 | 1,795 | 0 / 0 | Both pass; seven commands each, repeat + -O |
| CPython 3.14.3 | 169 | 1,795 | 0 / 0 | Both pass; seven commands each, repeat + -O |

Per interpreter, TC-020-01–06 execute 1 / 4 / 16 / 12 / 16 / 3 cases respectively (52 demo cases). REQ-019 groups execute 35 / 21 / 19 / 15 / 3 / 24 = 117 cases; the increment over the prior 114 is three new demo-gate subprocess probes grouped with the existing acceptance-gate tests. Thus 169 total, with zero failures/errors/skips. Artifact smoke independently inspects successful terminal evidence, expected timeout and typed rejection, exact text, actual installation paths and isolated interpreter flags. Six wheel pairs × seven commands × three invocations = 126 installed CLI invocations, plus existing provider smoke for each pair.

Ruff and strict mypy pass for fabric; scripts/check.sh passes all governance gates and 21 planning regressions; legacy requirements and public-data checks pass; git diff --check passes. No live service/hardware/network access is needed by the runtime. In-process tests count forbidden ambient effects; CLI subprocess I/O is the explicit test boundary. Fixed packaged catalogue loading is explicit resource I/O performed before the stronger file/environment/datetime denial check.

JUnit files from this run: /tmp/req020-provider312.xml, provider313.xml, provider314.xml and /tmp/req020-shared312.xml, shared313.xml, shared314.xml (each filename has req020- prefix). Complete artifact hashes, interpreter executable/version, and each installed command verdict are preserved in [artifact provenance](REQ-020-artifact-provenance.json). Local temporary environments are discarded by the verifier.

## Reproduction

```bash
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime -q
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime --require-binding-runtime --require-state-runtime --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req020-review-artifacts
```

Both compatible distributions must be installed together (or present in a configured private index); artifact installs select both wheel paths explicitly with --no-index --no-deps, without network resolution. Builds require the documented build/hatchling tooling.

## Artifact Hashes

Direct and sdist-derived wheel hashes match; all hashes below are identical across the three tested interpreters.

| Artifact | SHA-256 |
|---|---|
| direct/ai_family_state_schema-0.1.0-py3-none-any.whl | `8e3746304530d520ac8f5d07f0b60e70d901ca9e3fda92865417558fb854e1fe` |
| sdist/ai_family_state_schema-0.1.0.tar.gz | `1ac791febfe84770c1ea315fc0a8519de2cfaff650191b3cf398d7316fdf1dfc` |
| direct/ai_family_home_device_fabric-0.1.0-py3-none-any.whl | `e8fc63e7bad77514b8484388d0f8608328c7e9b8f4cef2e94a0e75b5db39b7f2` |
| sdist/ai_family_home_device_fabric-0.1.0.tar.gz | `c7c9cf1bedb2757c6736280f62b0e580c4cf1ff1e4799f6b9b4ea0f748b3e20c` |
| derived/ai_family_home_device_fabric-0.1.0-py3-none-any.whl | `e8fc63e7bad77514b8484388d0f8608328c7e9b8f4cef2e94a0e75b5db39b7f2` |
| derived/ai_family_state_schema-0.1.0-py3-none-any.whl | `8e3746304530d520ac8f5d07f0b60e70d901ca9e3fda92865417558fb854e1fe` |

## Deferred External Review

Review proposed TC text, automated TC code and implementation together. Human advancement authorization supplies scheduling only. No independent evaluator signature, ready operation, bot-review request, queue operation, merge or lifecycle advancement beyond req_impl is part of this delivery.

## Follow-up Fix Evidence

The initial e54a637 / 169-case record above is historical. Subsequent fixes for the human-supplied implementation pre-review are recorded separately in [fix evidence](REQ-020-pre-review-fixes.md) and [updated artifact provenance](REQ-020-fix-artifact-provenance.json), including 177 required fabric/demo cases per interpreter and detected output-event/repeat-guard/revision-filter mutations. The shared source is unchanged. Lifecycle and independent-review boundaries remain unchanged.
