# REQ-037 external combined review handoff

Prepared on 2026-11-11 for [draft PR #76](https://github.com/rushwing/ai-family/pull/76).
Implementation baseline: `f293c9ffc134ef9b2117138dee77644f1f1457c9`, against
`94a4f6379b7c6db850494a7a5e431728de453d47`. Later delivery evidence changes
documentation only.

Human-001 authorized combined specification, proposed TC criteria, runtime and
verification with an explicit stop at `req_impl` for external review. The sole
[REQ-037](../features/REQ-037.md) remains `req_impl / generator-001`, AC1–AC4
unchecked. All four TC documents remain generator-authored drafts. This packet
supplies no independent TC approval, evaluator signature or lifecycle transition.

Review the proposed criteria independently before assessing their implementation
mappings. Passing generator tests cannot establish that criteria are complete.

| Proposed criteria | Review focus | Recorded JUnit mappings |
| --- | --- | --- |
| [TC-037-01](../test-cases/TC-037-01.md) | Exact home/device/capability/version/action selection and ordered reasons | 12 |
| [TC-037-02](../test-cases/TC-037-02.md) | Four read-only sensors; switch/curtain schemas; no coercion or fallback | 34 |
| [TC-037-03](../test-cases/TC-037-03.md) | Bounded plain JSON; immutable configuration; isolation, diagnostics and zero ambient/provider effects | 41 |
| [TC-037-04](../test-cases/TC-037-04.md) | Missing/broken/skipped runtime gates; CI wiring and isolated installed artifacts | 10 |

Counts overlap and are not unique-case totals or independent approvals.

Read [action_validation.py](../../../toolsets/iot/home-device-fabric/src/home_device_fabric/action_validation.py),
[source tests](../../../toolsets/iot/home-device-fabric/tests/test_action_validation.py),
[gate probes](../../../toolsets/iot/home-device-fabric/tests/test_gate.py),
[installed smoke](../../../toolsets/iot/home-device-fabric/tests/action_validation_artifact_smoke.py)
and [CI wiring](../../../.github/workflows/ci.yml) against the REQ contract.
Semantic validity grants no permission: trusted identity, policy, confirmation,
audit, availability, resolution and actual dispatch remain separate caller
responsibilities. No HTTP/MCP route, provider mapping or physical write is added.

[Implementation evidence](REQ-037-runtime-implementation.md) records 2,056 full
fabric cases with all seventeen required-runtime flags and zero skips, followed
by 228 passing resumed validator/gate cases. Ruff, strict mypy and governance
passed. [Provenance](REQ-037-artifact-provenance.json) binds the clean baseline,
JUnit digest, runtime and distribution hashes and official dependency digests;
both wheel pairs passed all normal/optimized installed smoke families, including
four action-validator runs with 22 explicit checks each.
[Mutation evidence](REQ-037-mutations.json) records six killed faults against
unchanged runtime/test hashes. These are generator checks, not independent review.

The external reviewer should identify the reviewed commit, approve or revise
TC criteria, assess AC1–AC4 and record findings, executed checks and environment
limits. Keep readiness, final acceptance and merge separate from this delivery.
