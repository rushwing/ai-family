# REQ-020 Implementation Pre-review Fixes

[generator-001] Fixes under human-001’s request to fix all supplied local pre-review findings. Both supplied reports explicitly disclaim independent T03/T07/T10/T13 signatures. Remain req_impl / generator-001 and PR #40 draft. This record supplies local fix evidence only.

Tested source tree committed as `25eedfece49a0fde5fc88eb7042f3adefd174e09`, based on reviewed delivery `d2f5b98a4dff64952e1af95f121fc6f4e858591e`. Tests/builds ran on the identical working tree immediately before the fix commit. Source platform: Linux 6.12.62+rpt-rpi-2712 aarch64.

## Finding Disposition

| Finding | Disposition |
|---|---|
| F-1 lifecycle | Keep the human’s explicit req_impl stopping instruction. An explicit external-review assignment must record a later handoff to req_impl_review and its evaluator owner before review work. A local pre-review report and a fix instruction do not supply that assignment. REQ records the reason. |
| F-2 TC attribution | Preserve the established owner=actual text designer convention. Here the actual proposed text designer is generator-001 under the documented combined-delivery exception; separately attribute code author generator-001 and independent reviewer pending/unassigned. Do not invent evaluator authorship. All six TCs and API/REQ state this explicitly. |
| F-3 revision filter | Add model capability_version=1; filter descriptors by exact (ID, revision). Regression admits a second descriptor revision and asserts only the supported first revision is emitted. |
| F-4 nonexistent sensor action | Annotate write_temperature as a nonexistent negative-test action, in source/API/README. Sensor descriptor remains read-only with no actions. |
| F-5 provider reconstruction | Explain the frozen-at-construction attempt script and separation of persistent caller projection from the dispatch provider’s initially unknown snapshots. |
| F-6 CLI diagnostics | Retain required fixed value-free diagnostics; document direct library API tracebacks for debugging, and comment the exception boundary. Existing CLI tests verify programming-error details do not leak. |
| P2-A output events | Assert emitted descriptors exactly match canonical revision-1 descriptors, including empty events, in in-process tests, all seven CLI tests and installed-wheel smoke. |
| P2-B gate environment | Actual copied pytest hooks resolve only local runtime stubs using an explicit import finder; absent modules cannot fall back to real installed packages. Remove cached runtime imports in the child. Present and absent branches both run without ambient runtime. Optional collection exempts only gate self-tests; required flags still reject absence/skips. Nested regression runs six gate probes in provider-only and entirely absent layouts and asserts 6 passed, no skips. |
| Information-C repeat guard | Inject a duplicate on same-horizon re-advancement after real scheduling, State/Action helpers and terminal settlement, for success and timeout. Both must raise expectation_failed. This guard checks same-horizon repetition, not future queued observations. |
| Fixture/I-O observations | README distinguishes packaged CLI stimuli from TC-019-only fixtures. Autouse guard comments cross-reference the stronger file/environment/datetime-denial test after fixed resource loading. |
| Environment notes | README documents writable canonical TMPDIR and equivalent virtualenv installs when ensurepip is absent, while retaining named CI checks. |

## Verification

| Local interpreter | Required fabric/demo | Failed / skipped | Installed direct / sdist-derived pairs |
|---|---:|---|---|
| CPython 3.12.12 | 177 | 0 / 0 | Both pass all seven commands, repeat + -O |
| CPython 3.13.5 | 177 | 0 / 0 | Both pass all seven commands, repeat + -O |
| CPython 3.14.3 | 177 | 0 / 0 | Both pass all seven commands, repeat + -O |

TC-020-01–06 now execute 5 / 4 / 16 / 14 / 16 / 3 = 58 cases each interpreter. REQ-019 markers execute 35 / 21 / 19 / 15 / 3 / 26 = 119 (including eight gate self-tests rather than six). Total 177; the increase from 169 is four descriptor cases, two repeat-guard cases and two runtime-absent gate-self-test cases. JUnit: /tmp/req020-followup312.xml, followup313.xml and followup314.xml (all prefixed req020-).

Ruff and strict mypy pass. Governance gates and 21 planning regressions pass. Shared source, mock.py and __init__.py remain identical to main; the prior 1,795-case six-flag shared results remain historical prerequisite evidence, not a claimed new local rerun. Current-head GitHub CI is verified after push and recorded in the PR description.

Six newly built wheel pairs run 126 installed CLI invocations total. Their smoke independently locks canonical output descriptors and empty events as well as existing completion/rejection, exact text, isolated import provenance and optimized behavior. Direct and derived wheel hashes match across all tested interpreters. Complete hashes/interpreter executable/version and command verdicts are preserved in [fix artifact provenance](REQ-020-fix-artifact-provenance.json); initial e54a637 artifact evidence remains unchanged for historical attribution.

## Isolated Mutation Checks

Source/tests were copied to temporary trees, with each child import path verified to select the mutated copy; the live worktree was not mutated. Each selected regression fails (pytest exit 1) after the corresponding mutation:

| Mutation | Regression result |
|---|---|
| fake_output_event | 3 failed, 55 deselected in 0.21s |
| remove_repeat_guard | 2 failed, 56 deselected in 0.13s |
| drop_revision_filter | 1 failed, 57 deselected in 0.13s |

The fake-output-event mutation changes emitted events to {changed: 1}; the repeat mutation changes the expectation_failed raise to pass; the revision mutation drops the model revision constraint. These checks demonstrate that the new assertions guard the reported holes rather than merely mirror successful execution.

## Reproduction

```bash
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime -q
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests/test_gate.py -q
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req020-fix-review-artifacts
```

The second command runs gate probes without requiring runtime flags; those probes supply their own present/absent stubs and independently exercise required mode inside subprocesses. On platforms without writable /tmp, substitute a writable canonical TMPDIR for artifact paths. External text/code/runtime acceptance and AC checkboxes remain pending.
