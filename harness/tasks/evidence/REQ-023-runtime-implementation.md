# REQ-023 — Implementation Delivery Evidence

[generator-001][2026-10-14] Delivered under the human combined TC/runtime
authorization in [REQ-023](../features/REQ-023.md), reaffirmed by “Create a PR for
the implementation (till req_impl step) and I will ask for external review.”
Specification PR #48 was merged from final head
818e2ad72db120b4a76541f029a4c3ee14e40d66 as 0bad1e7. This delivery stops at
req_impl / generator-001, with draft [PR #49](https://github.com/rushwing/ai-family/pull/49), eight unchecked ACs
and six implemented TCs. The generator authored the proposed TC text and code
under the human exception; no independent T03/T07/T10/T13 approval is claimed.

## Tested source and behavior

Original delivery runtime, tests, CI and artifact source:
`bcc459740c739ce5b37d012017de806e0861b5e0`. The initial evidence and PR-number commits
were documentation only. The subsequent human-authorized pre-review follow-up
changes runtime/tests; this section and its numbers describe the original build.
See [fix disposition](REQ-023-pre-review-fixes.md) and
[revised provenance](REQ-023-fix-provenance.json) for current validation. Linux aarch64; CPython 3.12.12, 3.13.5 and 3.14.3.
Existing shared-contract and provider/mock/caller/demo/scenarios/conformance
runtime modules and top-level exports are unchanged.

The new adapter-local module exposes HARestClient, HARuntimeInfo and HARestError.
It reuses accepted HAConfiguration and its explicit credential seam. Each call
owns a fresh HTTPX transport and streamed response, sends exactly one GET to
/api/config, and projects only the validated version. The transport API avoids
AsyncClient's URL-bearing INFO logger and removes redirect/cookie machinery.
TLS verification and no-retry/no-environment settings are explicit. Dependency
exceptions are discarded before constructing public errors; cause/context stay
empty. No credential loading, device writes, generic request API or live HA
certification is supplied.

Single-operation admission rejects overlapping requests immediately, and close
drains through an operation completion event rather than awaiting the caller's
whole task. The overall monotonic request budget includes setup/headers/body;
an observed deadline wins over ordinary outcomes. Cancellation propagates after
one cancellation-safe, aggregate 1000 ms cleanup guard. Synchronous setup or
finalization, event-loop scheduling and resolver workers cannot be forcibly
preempted; this is not a hard real-time worker-termination guarantee.

## Source verification

For each interpreter, with both local distributions installed:

```bash
python -m pytest -c toolsets/iot/home-device-fabric/pytest.ini toolsets/iot/home-device-fabric/tests --require-provider-runtime --require-demo-runtime --require-conformance-runtime --require-ha-configuration-runtime --require-ha-rest-runtime -q --junitxml=/tmp/req023-testsVERSION.xml
python -m pytest -c libs/state-schema/pytest.ini libs/state-schema/tests --require-inventory-runtime --require-binding-runtime --require-state-runtime --require-capability-runtime --require-initial-capabilities-runtime --require-action-runtime -q --junitxml=/tmp/req023-sharedVERSION.xml
```

All three interpreters pass **569 fabric and 1795 shared tests**, zero failures,
errors or skips. Fabric preserves the 462-test baseline and adds 107 cases:
101 REST tests and six hermetic required-mode probes. Actual source markers and
JUnit names produce the following counts per interpreter:

| TC | Executed | Failed/errors | Skipped |
| --- | ---: | ---: | ---: |
| TC-023-01 | 1 | 0 | 0 |
| TC-023-02 | 55 | 0 | 0 |
| TC-023-03 | 33 | 0 | 0 |
| TC-023-04 | 8 | 0 | 0 |
| TC-023-05 | 4 | 0 | 0 |
| TC-023-06 | 6 | 0 | 0 |

Literal expectations cover exact API/ID/result/error shapes; version boundaries,
prerelease examples, invalid UTF-8/JSON/duplicate keys/non-finite values; media,
charset and compression rejection; streamed 262143/262144/262145-byte limits
independent of declared length; status-before-body classification; sensitive
dependency chains; failure recovery; 1 ms deadline races; concurrent busy/close
ordering; cancelled close waiters; repeated operation cancellation during
cleanup; cleanup-guard expiry; and actual loopback wire/proxy/cookie/INFO-log,
redirect, connection-refusal, DNS-error, TLS and trickling-deadline behavior.
Expectations do not reuse runtime validators/defaults as their oracle.

The REST fixture permits numeric loopback sockets and explicit clocks/TLS
entropy. Existing pure-test counted ambient-effect denial remains active. Fake
HTTP server workers are drained before another test can reinstate that denial.
Hermetic gate stubs prevent ambient installed fallback and prove missing
package/module/HTTPX rejection, optional absence, mandatory skip failure and
present-runtime success. Fictional credentials are never printed in evidence.

## Installed distributions and dependency provenance

For each interpreter:

```bash
python toolsets/iot/home-device-fabric/tests/build_artifacts.py --out-dir /tmp/req023-artifactsVERSION
```

All builds and smokes pass. The builder resolves binary HTTPX dependency wheels
once per run and hashes them, then installs each compatible direct/sdist-derived
wheel pair and dependency closure offline into fresh environments outside the
checkout. pip check passes. Existing provider/demo/conformance/configuration
smokes remain, with a copied independent REST script run under -I and -O -I.
Explicit require checks survive optimization and use actual installed HTTPX for
wire headers, version-only projection, timeout, concurrent busy/close rejection,
draining close and untrusted TLS rejection. Six wheel pairs across three
interpreters produce twelve passing REST smoke records.

Resolved runtime closure on all three interpreters: HTTPX 0.28.1, httpcore 1.0.9,
h11 0.16.0, anyio 4.15.1, certifi 2026.7.22, idna 3.20 and typing_extensions
4.16.0. No HTTP/2/CLI/compression extras were requested. The minor HTTPX range is
bounded, but transitive dependencies are not repository-locked. Resolution may
change on future runs; the recorded wheel hashes identify this execution.

[Full artifact provenance](REQ-023-artifact-provenance.json) records tested
commit/platform/interpreters, source counts, distribution/sdist and dependency
wheel SHA256, installed distributions, and all smoke results. Hashes were
recomputed against the built files; installed REST module hashes match source.
Installed smoke counts are separate from pytest TC counts.

## Other checks and external review

Ruff, strict mypy (ten fabric source modules), governance gates, 21 planning
regressions, legacy requirements/public-data checks, local Markdown targets and
git diff --check pass. CI adds the fifth required fabric flag and REST artifact
smokes to its Python 3.12/3.13/3.14 jobs. CI status is inspected on the published
head separately from these local results.

External review should examine expectation independence, raw-response/error
privacy, request/cleanup deadline precedence, cancellation and draining-close
ordering, production transport policy, required-mode probes and installed
optimized checks. The user will arrange external review. This session does not
send reviewer messages, advance lifecycle, mark ready or merge this PR.


The later [F10 cleanup follow-up](REQ-023-f10-fixes.md) records the next runtime
revision and current validation. The counts/hashes in this document remain
historical evidence of the preceding delivery.
