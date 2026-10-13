# REQ-022 — Combined Implementation Evidence

[generator-001][2026-10-13] Delivered under [human delegated decisions and combined authorization](../features/REQ-022.md). Specification PR #45 merged at 2026-10-13T08:51:53Z as a82cbb72cde5ac55ed1e7040e7185022e0a6872e from final head 829ee36643eaebd0139a95cb492f0399458c5dd7, after three successful applicable checks and six expected path-filter skips. Implementation [PR #46](https://github.com/rushwing/ai-family/pull/46) stays draft, req_impl / generator-001. All ACs remain unchecked; TC text designer and code author are generator-001 under the human exception. No independent T03/T07/T10/T13 signature or external acceptance is claimed.

## Tested Source and Scope

Runtime/TC/artifact source: 64bc81d6aa3e2514ed115db0154d30143900dbae. Linux aarch64 / CPython 3.12.12, 3.13.5, 3.14.3, installed editable compatible packages in /tmp/req019-env, /tmp/req019-env313, /tmp/req019-env314. Later evidence/REQ updates are documentation only. Existing shared contracts and provider/mock/caller/demo/scenarios/conformance runtime modules and top-level exports are unchanged. New adapter-local HAConfiguration supplies strict explicit settings/separate token, immutable context, finite reconnect inspection and redacted diagnostics. No network/authentication, secret loaders or live certification.

## Source Acceptance

For each interpreter:

```bash
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime --require-conformance-runtime --require-ha-configuration-runtime -q --junitxml=/tmp/req022-final-testsVERSION.xml
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime --require-binding-runtime --require-state-runtime --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q --junitxml=/tmp/req022-final-sharedVERSION.xml
```

Each interpreter passes 462 fabric and 1795 shared cases, zero failures/errors/skips. Fabric retains the 259-case baseline and adds 203 REQ-022 cases (197 configuration plus six hermetic gate probes). Per-TC source counts derive from JUnit records matched to actual source markers:

| TC | Executed per interpreter | Failed | Skipped |
|---|---:|---:|---:|
| TC-022-01 | 24 | 0 | 0 |
| TC-022-02 | 75 | 0 | 0 |
| TC-022-03 | 25 | 0 | 0 |
| TC-022-04 | 72 | 0 | 0 |
| TC-022-05 | 1 | 0 | 0 |
| TC-022-06 | 6 | 0 | 0 |

Independent expectations enumerate normalized DNS/IPv4/IPv6 roots, explicit default/zero-padded ports, exact 2048 URL and 8192 token limits, malformed authority/delimiters/paths/percent forms, strict numeric types/ranges/order, capped schedules and 1/32 attempt budgets. No runtime defaults/validators are used as expected-value oracles. Shape/unknown-key/primitive-subclass rejection occurs without user override invocation. Multiple instances, input/snapshot mutation and repeated init/assignment/deletion verify stable immutable context.

Redaction checks cover repr/str/container repr, exact snapshots/JSON, caller logging, exceptions/args/structured fields/chain, and refusals of vars/asdict/default JSON/pickle/copy/direct __getstate__/__reduce__. Credential wrapper representation and raw serialization refusal are also checked. Distinctive token/prefix/suffix/hash/length markers and private endpoint markers are searched independently; snapshots expose no derived metadata. Deliberate transport access and private/debugger/memory exclusions are explicit. IPv4/IPv6 parser errors are converted outside handlers, so fixed errors have no parser cause/context.

Counted network/process/clock/random guards remain active, extended to nanosecond/process clocks. Dedicated post-import file/environment/datetime denial covers construction, inspection and malformed settings paths; swallowed attempts still fail. Caller logging tests supply fixed logging-only timestamps while runtime time APIs stay denied. Required-configuration probes block ambient-installed fallback and exercise absent package/module/shared dependency, optional absence, mandatory skip failure and present/no-skip success. Gate-only probes remain runnable without runtime packages.

## Installed Artifact Acceptance

For each interpreter:

```bash
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req022-final-artifactsVERSION
```

All builds and smokes succeed. Build both compatible distributions' direct wheels/sdists and sdist-derived wheels; install each pair into fresh venvs outside checkout with --no-index --no-deps. Retain existing provider/demo and conformance inventory/forwarding/defective-driver checks. A copied independent configuration script imports only installed packages, without pytest or checkout assets, under -I and -O -I. Explicit require checks survive -O and verify accepted normalized construction, token transport access, detached exact redaction, default eight-delay tuple, immutability, four fixed rejection/chain cases and six raw export refusals. Token/endpoint/derived markers are absent from collected ordinary outputs.

Six wheel pairs across three interpreters produce 12 passing configuration smoke records, each with redaction=true, four rejected invalid constructions, six refused exports and schedule_count=8. [Full provenance](REQ-022-artifact-provenance.json) records tested commit/interpreters/platform, per-TC counts, wheel/sdist SHA256 and existing plus configuration smoke outcomes. Recorded hashes were independently recomputed against built files. Installed counts are distinct from pytest per-TC counts.

## Other Checks and Review Boundary

Ruff and strict mypy pass for fabric runtime/tests and all nine source modules. Governance gates and 21 planning regressions, legacy requirements/public-data validation, local Markdown target checks and git diff --check pass. CI extends the existing 3.12/3.13/3.14 fabric jobs with the new required flag and paired artifact smoke; workflow changes also trigger existing shared-contract checks. Final-head CI is read separately from local source evidence.

Q1–Q6 dispositions remain in REQ-022 and the [proposed API/TC contract](REQ-022-api-contract.md), with README usage. Deepseek should review expectation independence, hostile endpoint/error handling, introspection/serialization limits, mandatory gates, installed optimized validation and compatibility. Stop at req_impl / generator-001, with draft PR #46, eight unchecked ACs and six implemented TCs. Human will arrange external review and later lifecycle disposition; no independent approval or implementation merge is inferred.
