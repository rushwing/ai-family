# REQ-021 — Proposed Combined-delivery API and TC Contract

[generator-001][2026-10-13] Proposed under human-001's explicit combined TC/code/runtime authorization. This freezes implementation/acceptance interfaces for this delivery; it is not an independent T03/T07/T10/T13 signature. Independent external review remains pending after req_impl. Q1–Q6 dispositions are recorded in [REQ-021](../archive/done/features/REQ-021.md).

Exports from home_device_fabric.conformance: ConformanceDriver(provider: ProviderProtocol), mock_factory(configuration_data: object) -> ConformanceDriver, run_conformance(factory=mock_factory) -> dict, expected_inventory() -> list[dict], validate_report(report: object) -> bool, canonical_json(value: object) -> str. Factory receives a fresh detached complete validated MockConfiguration JSON containing all explicit stimuli before construction; the returned object must be a ConformanceDriver instance or subclass instance, wrapping a provider that satisfies the full existing ProviderProtocol. Returning a bare provider is a setup_failed result. ConformanceDriver.dispatch(task, *, binding, attempt_id, verdict) delegates to provider.submit only for dispatch and suppresses replay/conflict/offline/invalid. Custom drivers may override that caller policy seam. Provider.advance owns offline virtual time; live support is outside this profile.

CLI: python -m home_device_fabric.conformance, no supported arguments. Exactly one sorted compact finite JSON object plus newline; exit 0 iff validate_report passes, 1 for failed checks/setup/inventory, 2 for invalid arguments with fixed invalid_arguments stderr. Runtime checks survive -O.

Report exact fields: schema_version (strict int 1), simulation (true), profile (offline-provider-v1), inventory_version (strict int 1), inventory_sha256 (pinned below), expected_cases (complete ordered list of case_id/obligation), cases (same ordered IDs/obligations, executed bool, status passed/failed, evidence dict, error null or fixed code), counts (total/executed/passed/failed/skipped strict ints), passed (bool). Every attempted case, including setup failure, is executed=true; setup errors report failed with setup_failed, no raw exception. Case-check errors have fixed codes. skipped is always zero. validate_report rejects any unexpected/missing fields, changed ordering, duplicate/missing/extra cases, inconsistent statuses/errors/counts/verdicts, non-finite/non-JSON values or altered inventory/version/hash. It returns true only for complete passing reports; failed reports remain diagnostic JSON. Inventory hash detects drift against the trusted pinned package/verifier, not malicious replacement of the verifier.

Case inventory version: 1. Count: 51. SHA256 of canonical ordered ID/obligation list: `0cb57579e3eb82bb1d7c73722f1c5e3c386427d45c7efde9ed011a5c7f18e6bd`.

```json
[
  {
    "case_id": "discovery",
    "obligation": "provider"
  },
  {
    "case_id": "catalogue",
    "obligation": "caller"
  },
  {
    "case_id": "provider-binding",
    "obligation": "provider"
  },
  {
    "case_id": "provider-arguments",
    "obligation": "provider"
  },
  {
    "case_id": "provider-accepted",
    "obligation": "provider"
  },
  {
    "case_id": "provider-support",
    "obligation": "provider"
  },
  {
    "case_id": "provider-attempt",
    "obligation": "provider"
  },
  {
    "case_id": "provider-action",
    "obligation": "provider"
  },
  {
    "case_id": "provider-revision",
    "obligation": "provider"
  },
  {
    "case_id": "switch-on",
    "obligation": "integration"
  },
  {
    "case_id": "switch-off",
    "obligation": "integration"
  },
  {
    "case_id": "curtain-closed",
    "obligation": "integration"
  },
  {
    "case_id": "curtain-open",
    "obligation": "integration"
  },
  {
    "case_id": "curtain-partial",
    "obligation": "integration"
  },
  {
    "case_id": "switch-timeout",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "switch-mismatch",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "switch-stale",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "switch-wrong-epoch",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "switch-deadline-tie",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "switch-late",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "curtain-timeout",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "curtain-mismatch",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "curtain-stale",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "curtain-wrong-epoch",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "curtain-deadline-tie",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "curtain-late",
    "obligation": "mock-scheduling"
  },
  {
    "case_id": "switch-failed",
    "obligation": "integration"
  },
  {
    "case_id": "curtain-failed",
    "obligation": "integration"
  },
  {
    "case_id": "switch-offline-unknown",
    "obligation": "caller"
  },
  {
    "case_id": "switch-offline-known",
    "obligation": "caller"
  },
  {
    "case_id": "curtain-offline-unknown",
    "obligation": "caller"
  },
  {
    "case_id": "curtain-offline-known",
    "obligation": "caller"
  },
  {
    "case_id": "temperature-offline-unknown",
    "obligation": "caller"
  },
  {
    "case_id": "temperature-offline-known",
    "obligation": "caller"
  },
  {
    "case_id": "switch-invalid-0",
    "obligation": "caller"
  },
  {
    "case_id": "switch-invalid-1",
    "obligation": "caller"
  },
  {
    "case_id": "switch-invalid-2",
    "obligation": "caller"
  },
  {
    "case_id": "switch-invalid-3",
    "obligation": "caller"
  },
  {
    "case_id": "curtain-invalid-0",
    "obligation": "caller"
  },
  {
    "case_id": "curtain-invalid-1",
    "obligation": "caller"
  },
  {
    "case_id": "curtain-invalid-2",
    "obligation": "caller"
  },
  {
    "case_id": "curtain-invalid-3",
    "obligation": "caller"
  },
  {
    "case_id": "request-action",
    "obligation": "caller"
  },
  {
    "case_id": "request-member",
    "obligation": "caller"
  },
  {
    "case_id": "request-revision",
    "obligation": "caller"
  },
  {
    "case_id": "temperature-observe",
    "obligation": "caller"
  },
  {
    "case_id": "temperature-write",
    "obligation": "caller"
  },
  {
    "case_id": "replay",
    "obligation": "caller"
  },
  {
    "case_id": "conflict",
    "obligation": "caller"
  },
  {
    "case_id": "replay-invalid-type",
    "obligation": "caller"
  },
  {
    "case_id": "provider-ordering",
    "obligation": "provider"
  }
]
```

Independent expectations are declared in conformance-owned fixtures and fixed catalogue content, never taken from demo verified/expected_task fields. Conformance does not import caller.py/demo.py. Acceptance independently checks known values and report identity; defects inject observable behavior rather than alter expected results. TC-021-01–06 correspond to seam/discovery, validation/State, action/deadlines, replay/offline, reports/defects, and gates/installed artifacts. TC text owner and code author are generator-001 under the human exception, with external review explicitly pending.

Installed smoke: paired --no-index --no-deps wheel installs, direct and sdist-derived, outside checkout under -I; repeated CLI exact stdout, -O, forwarding wrapper and defective identity wrapper invoked through the installed packaged runner. Retain existing provenance hashes and add conformance case counts, report hash and detected-case IDs.

Malformed/non-finite driver evidence is replaced with evidence={"diagnostic":"invalid_evidence"}, error=check_failed and failed status so serialization stays finite/value-free. The required session gate separately invokes the full runtime inventory even when pytest selection omits conformance TCs. Six TC records remain implemented, with execution evidence in [implementation report](REQ-021-runtime-implementation.md); no independent acceptance signature is supplied.

## Fixed Failure Vocabulary

These meanings describe the existing implementation; they add no API behavior or independent approval. Every failed case has status=failed, error set to a fixed code and executed=true. The runner continues with the remaining required inventory. Diagnostic codes/messages omit supplied exception values and chains; ordinary evidence retains the observable fictional contract values.

| Code | Meaning |
|---|---|
| setup_failed | Factory construction/configuration admission raises, the factory returns an object outside ConformanceDriver, or its provider fails the full ProviderProtocol check. |
| check_failed | An unexpected exception occurs during a case check, or evidence cannot pass strict finite JSON validation/serialization. Configuration errors outside the factory seam also reach this case exception boundary. |
| identity_mismatch | Discovery identity, exact supported revision, binding, repeated/fresh discovery or detached export expectations differ. |
| catalogue_mismatch | The selected exact revision-1 descriptors differ from the fixed expectation snapshot. |
| invalid_dispatch | Actual dispatch/delivery effects violate the expected rejection, action or caller replay/offline counts. |
| state_mismatch | Initial, reported or availability State, ordering, value/type or applied/rejected input expectations differ. |
| completion_mismatch | Task state, ACK behavior, physical outcome, intermediate completion or terminal handling differs. |
| delivery_mismatch | Full yielded records/order/times, public delivery log, deadline outcome, repeated advancement or final virtual time differs. |
| rejection_mismatch | The expected provider error code or caller rejection differs. |
| policy_mismatch | Caller replay classification differs, or the default driver receives an unsupported verdict. |

`invalid_evidence` is a diagnostic marker inside evidence, not an additional error code: evidence becomes exactly {"diagnostic":"invalid_evidence"}, error=check_failed and status=failed when evidence is not strict finite JSON or cannot serialize. This replacement allows a finite report instead of echoing malformed values. `validate_report` returns false for these failed reports.

## Reproduction and Attribution

CLI subprocess acceptance uses python -I and therefore ignores PYTHONPATH. Install both compatible packages into the pytest interpreter (editable installs or paired wheels); PYTHONPATH-only discovery in the parent process does not satisfy isolated child imports.

TC-021-01–06 owner identifies the actual proposed-text designer, generator-001; automated code author is also generator-001 under the explicit combined-delivery exception. A later independent reviewer and disposition are recorded separately and never inferred from that owner field. Inventory hashing remains a drift check against the trusted verifier, not a supply-chain signature or evidence authentication.

## Human Final Disposition

Human-001 explicitly accepted the combined delivery and authorized PR #43 merge. [Closeout evidence](REQ-021-review-acceptance.md) records merge and done archival. This supersedes historical pending-acceptance statements; actual proposed-text/code attribution remains generator-001, without invented independent reviewer signatures.
