# REQ-023 — Human-authorized local pre-review fixes

[human-001][2026-10-14] Supplied the local pre-review of PR #49 head b427167b,
explicitly not an independent review signature, and instructed “Fix all findings”.
[generator-001] Implements the follow-up under the existing combined-delivery
exception. Remain req_impl / generator-001; eight ACs unchecked, six TCs
implemented, PR #49 draft and unmerged. This record is local disposition and
validation, not T03/T07/T10/T13 acceptance.

## Disposition

| Finding | Change and falsifier |
| --- | --- |
| F0 | All non-200/401 statuses classify as http_error. Only exact integer 100–599 statuses are projected; nonstandard statuses project None. Real HTTP 600/999 retain ID and finite error shape; 599 retains its status. Constructor negative cases separately retain diagnostic range/type validation. |
| F1 | A real bound, non-listening loopback endpoint counts TCP connect calls; exactly one is allowed. retries=1 and retries=3 each fail this test. |
| F2 | Ordinary response/transport close exceptions preserve the classified success/error and do not leak raw exceptions. Both owned closes are attempted under the existing aggregate guard; resource references are cleared afterward. Tests cover success, 401, 404, invalid body, connection failure and cancellation, recovery, and cleanup expiry over success/401. return_exceptions=False and unconditional outcome overwrite are detected. |
| F3 | Result/error pickle/copy/deepcopy reconstruct only validated projections. Error reduction excludes exception traceback/cause/context/notes; round-trip tests attach adversarial dependency bookkeeping and verify it is discarded. Client raw exports remain forbidden. |
| F4 | Specification, proposed contract, TC-023-01 and README explicitly distinguish closed context entry RuntimeError("client_closed") from correlated runtime_info HARestError("client_closed"). |
| F5 | Preserve the frozen post-cleanup deadline check. Added a deterministic cleanup clock probe where 401 becomes timeout. This is deliberate semantics, not a defect; external reviewer acceptance remains pending and is explicitly requested in the review scope. |
| F6 | Add exact remaining-budget connect/read/write/pool assertions, expired setup zero dispatch, close exception probes, code/ID/status constructor positives and negatives, synchronous-stream rejection before consumption, all three repeated-initialization/deletion guards and supported exception-bookkeeping assignment. Remove the duplicate string-type check after the exact-string predicate; keep typing via cast. Targeted mutation validation covers the reported non-equivalent gaps. |
| F7 | Contract/TC-023-05/README distinguish structural proxy exclusion (direct transport, no proxy configuration) from observable SSL_CERT_FILE trust_env behavior. Existing real probe remains. |
| F8 | README and TC-023-06 document standard-library venv/ensurepip requirements, the Android/Termux limitation and manual virtualenv setup; manual smoke is not represented as full builder/matrix evidence. |
| F9 | Record the real author and combined-delivery exception. External T07/T10 must derive expectations independently of author predicates/assertions. Local fixes do not grant T12/T13/readiness/merge; these remain explicit later decisions. No independent approval is fabricated. |

## Validation provenance

Updated runtime/test source is commit
`3c5b44abb24b1a13da5c045e41d567fd95259e5a`; documentation and execution evidence follow separately. The original
[delivery evidence](REQ-023-runtime-implementation.md) and
[artifact provenance](REQ-023-artifact-provenance.json) describe the historical
bcc45974 build. Revised matrix results and hashes are recorded in
[follow-up provenance](REQ-023-fix-provenance.json).

The targeted isolated mutation matrix changes only copied files outside the
checkout. Each mutation must fail its named regression, with pytest exit 1;
collection errors/timeouts do not count as detection. These are author-run
falsifiers, not independent reviewer evidence. Ordinary close failure can no
longer recategorize an HTTP error or successful read; aggregate guard expiry,
observed deadline expiry and caller cancellation retain their documented
priority. No claim is made that a failing third-party close released its resource
or that reference clearing erases immutable secrets/process memory.


## Executed follow-up results

Linux aarch64, CPython 3.12.12 / 3.13.5 / 3.14.3: each interpreter passed
612 fabric tests and 1795 shared tests, zero failures/errors/skips. The accepted
462-test fabric baseline remains; REQ-023 now contributes 150 cases (144 REST
and six required-mode probes), 43 more than the original delivery.
TC-023-01–06 counts are 5 / 56 / 61 / 17 / 5 / 6 on every interpreter.
Ruff 0.17.0 and strict mypy 2.4.0 passed on all three interpreters.

All six direct/sdist-derived compatible wheel pairs passed their existing
provider/demo/conformance/configuration smokes and twelve REST smoke executions
under -I and -O -I. Recomputed package and dependency wheel hashes match the
builder reports; every installed REST module hash matches the current source
(4a1d52824b897ab22cc29bf59a16dcd69ab0e58239ea2ef8bb9ce8bc6b950c73).
Runtime closure remains httpx 0.28.1, httpcore 1.0.9, h11 0.16.0, anyio 4.15.1,
certifi 2026.7.22, idna 3.20 and typing_extensions 4.16.0.

All 28 isolated targeted mutations were detected by assertion failures, including
retries=1/3, omitted phase extensions, gather exception propagation, ordinary
cleanup outcome overwrite, nonstandard status projection, diagnostic validators,
stream type, exhausted setup budget, all three reinitialization/set/delete guards,
exception-bookkeeping allowlist and safe result/error reconstruction. These are
targeted non-equivalent mutations; no claim of exhaustive mutation coverage is
made. Exact mutations, selectors, tool versions, per-TC/JUnit counts and complete
artifact/dependency reports are retained in the follow-up provenance.

Governance gates, 21 planning regressions, legacy requirements/public-data checks,
local Markdown targets and git diff --check passed. The runtime/test commit is
immutable; README clarification was present during builds and its hash is
recorded separately, with documentation/evidence committed afterward. No live HA
or Android/Termux builder run is claimed. Published-head CI is checked separately.
