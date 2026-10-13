# REQ-021 — Combined Implementation Evidence

[generator-001][2026-10-13] Delivery under [human combined authorization](../archive/done/features/REQ-021.md). Specification PR #42 merged as `4060033`; implementation [draft PR #43](https://github.com/rushwing/ai-family/pull/43) remains req_impl / generator-001. No independent evaluator signature or external text/code/runtime acceptance is claimed. AC1–AC8 remain unchecked; TC-021-01–06 are implemented with actual proposed-text designer and code author generator-001.

## Tested Source and Environment

Runtime/TC/artifact source: `81f023dda990f6affbd98d609d1ec1471b425ac2`. Linux aarch64, kernel 6.12.62+rpt-rpi-2712, glibc 2.41. CPython 3.12.12 / 3.13.5 / 3.14.3, compatible editable packages in /tmp/req019-env, /tmp/req019-env313, /tmp/req019-env314. Existing provider/mock, demo/caller/scenario and shared-schema runtime source is unchanged. New conformance modules use public boundaries and actual helpers.

## Source Acceptance

For each interpreter:

```bash
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime --require-conformance-runtime -q --junitxml=/tmp/req021-testsVERSION.xml
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime --require-binding-runtime --require-state-runtime --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q --junitxml=/tmp/req021-sharedVERSION.xml
```

259 fabric/provider/demo/conformance cases and 1,795 shared cases pass per interpreter; zero errors/failures/skips. Of the fabric cases, 76 are new test_conformance cases, three new missing-component probes carry tc021_06, and three expanded generic flag probes retain tc019_06 attribution. Existing 177-case baseline remains exercised. The required session gate separately executes and verifies the complete 51-case packaged inventory, including when pytest selection omits its TCs. Runtime report cases and pytest acceptance cases are distinct counts.

| TC | Executed per interpreter | Failed | Skipped |
|---|---:|---:|---:|
| TC-021-01 | 1 | 0 | 0 |
| TC-021-02 | 8 | 0 | 0 |
| TC-021-03 | 19 | 0 | 0 |
| TC-021-04 | 21 | 0 | 0 |
| TC-021-05 | 25 | 0 | 0 |
| TC-021-06 | 5 | 0 | 0 |

Counts derive from JUnit testcase records matched to actual source markers. Expanded generic gate probes remain attributed to their existing TC. Fixed report inventory version 1 contains 51 ordered ID/obligation pairs; SHA256 `0cb57579e3eb82bb1d7c73722f1c5e3c386427d45c7efde9ed011a5c7f18e6bd`.

Independent tests assert literal identity/revision/type/value, Task outcomes, full yielded records/times, rejection codes and effects. Forwarding factory yields the same report; seven defective wrapper/driver behaviors fail their specified checks and overall acceptance: identity, support, ACK, mismatched report, timeout tie, repeated delivery and replay dispatch. Gate probes reject absent shared/provider/conformance components and mandatory skips using local import stubs, with no ambient-package fallback. Gate self-tests execute without provider/demo runtime. File/environment/datetime guards allow only the declared shared catalogue resource; counted network/process/clock/random guards remain active, with explicit CLI subprocess reaping as a test boundary.

Report tests reject missing/duplicate/extra/skipped/failed/unexecuted IDs, inventory/hash/version/count/type changes, non-finite values and unexpected fields. Truncated runner inventory fails. Setup exceptions never echo supplied private values. Non-finite evidence from a faulty driver is replaced with fixed invalid_evidence diagnostics and a failed, finite report. CLI tests verify exact repeat/optimized JSON, exit 1 for failure and exit 2 with fixed stderr for invalid arguments.

## Installed Artifact Acceptance

For each interpreter:

```bash
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req021-artifactsVERSION
```

All builds/smokes succeed. Build both distributions' direct wheels/sdists and wheels derived from sdists, then install each compatible pair with --no-index --no-deps into fresh venvs outside the checkout. Existing provider smoke and seven-command demo repeat/optimized smoke remain effective.

Each pair additionally runs a copied independent acceptance script outside the checkout with -I and -O -I, importing only installed runtime packages. Each execution runs the full 51-case CLI three times (repeat and optimized), checks exact stdout/known inventory/counts/hash, and invokes the installed packaged runner through a forwarding wrapper and a defective identity wrapper. Forwarding passes; discovery detects identity_mismatch and overall acceptance fails for the defective wrapper. A forged truncated report is rejected. Explicit require() checks in this script remain effective under -O. The independent wrapper never loads runtime source from the checkout.

Six wheel pairs across three interpreters produce 12 conformance smoke records, 36 installed conformance CLI invocations, 12 passing forwarding runs and 12 detected defective runs. All report hashes agree across runs/interpreters. [Full artifact provenance](REQ-021-artifact-provenance.json) records source commit, wheel/sdist SHA256 values, interpreters, pair/mode, report/inventory hashes and defect detection. This is offline profile evidence, not live adapter or physical-device certification.

## Other Checks and Review Dispositions

Ruff check and strict mypy pass for fabric runtime/tests and all eight source modules. Governance gates, 21 planning regressions, legacy requirements/public-data validation, local Markdown target checks and git diff --check pass. No shared schema or provider/demo runtime behavior is changed. CI adds the distinct required-conformance flag to the existing three-version fabric job; source/check/driver/report changes fall under its existing path filters.

Q1–Q6 essential decisions are persisted in REQ-021 and the [proposed API/TC contract](REQ-021-api-contract.md), with README usage. The factory accepts explicit complete scripts and full ProviderProtocol; provider virtual-time advancement remains offline-only. Both library/CLI APIs and exact report/exit meanings are frozen. The inventory hash detects drift against the trusted verifier, not malicious verifier replacement or evidence authentication. Installed defect proof, paired no-index/no-deps installation, and conformance/demo responsibilities are explicit. No unresolved Q requires human selection for this implementation.

## Stop Boundary

Stop at req_impl / generator-001. Keep PR #43 draft, all ACs unchecked and TCs implemented pending external review. Do not infer req_impl_review, ready, bot-review, queue, done or implementation merge authorization. Later external assignment/acceptance must record its actual actor and legal handoff separately.
