# REQ-024 user-supplied static review disposition

## Authority and source

On 2026-10-15 human-001 supplied a static review of PR #51 head 3567b42.
The review reported no blockers, explicitly could not execute local tests, and
supplied no registered Harness reviewer identity. It is implementation feedback,
not an independent T03/T07/T10/T13 signature or acceptance. This session acts as
generator-001 within REQ-024's existing combined-delivery authority and keeps
req_impl, eight unchecked ACs and six implemented TCs. The draft PR stays unmerged.

## Findings and disposition

| Finding | Disposition |
|---|---|
| 1: historical dependency hashes | Confirmed the mismatch against fresh official release metadata; opened [BUG-032](../bugs/BUG-032.md) and saved [the audit](REQ-023-dependency-digest-audit.json). The claim that this PR overwrites the old files is incorrect: all three old Git blob IDs match base f2e201b at reviewed head 3567b42. Preserve those records. No original wheelhouse is available, so the discrepancy cause and original dependency bytes remain unverified. |
| 2: platform and Windows provenance | Builder now records platform, system, machine, Python implementation, version and executable. Follow-up validation records the actual Windows interpreter/environment alongside executed test counts. Historical initial-source evidence stays unchanged and explicitly historical. Different pure-Python wheel hashes cannot be explained by architecture alone; exact archive reproduction needs the original bytes/build environment, which we do not have. No shared runtime/package source changed. |
| 3: CI wiring | Added an always-running governance checker for the actual complete fabric pytest command and all six required flags, plus mutation tests removing each flag, replacing execution with echo and removing the job. The review's exact silent-green example overstates the prior behavior: removing just the WS flag neither skips an installed runtime nor disables the other five flags' zero-skip check. The explicit new invariant still prevents that wiring drift independently. |
| 4: excessive test allowances | Fake async tests now permit only the event-loop monotonic clock and self-pipe setup. Individual wire markers permit numeric-loopback networking, frame entropy and logging timestamps; only the TLS fixture permits openssl subprocesses. getenv/system/urllib stay denied. A separate synchronous construction test also denies file/environment reads and verifies attempted effects cannot be swallowed. The historical REQ-023 boundary is described accurately and remains separate. |
| 5: repeated close after BaseException | Worker finally-cleanup completes before its result is drained. run propagates the original failure; aclose consumes that already-owned result and drops the worker reference, so concurrent and repeated closers do not replay stale exceptions. Receive/send/close BaseException probes now close repeatedly afterward. |
| 6: lost failure reason | Closed snapshots retain the last known finite reason and retry ordinal. Fake and installed smoke checks assert auth_failed/reconnect_exhausted remain inspectable after repeated close. Process-control failure publishes internal_error before propagation. |
| 7: vacuous timeout assertion | Both timeout branches assert concrete socket state: auth sockets close exactly once; connect-timeout sockets remain unused with no sends/closes. |
| 8: unreachable private logger via caplog | Attach a direct DEBUG-capable handler to the actual isolated logger. The wire exchange emits nothing; a safe sensitivity probe temporarily enables the same logger and proves that handler catches a record. Restore logger configuration afterward. |
| 9: brittle sequence/surface assertions | Check strictly increasing public sequence values without fixing internal publication counts; pin the exact public callable method set to run/aclose/health. |
| 10: gate row gaps/import exceptions | Added optional missing-dependency and optional/required import-time RuntimeError rows. Ordinary import errors become required-mode UsageError 4 or explicit optional skips, not an internal pytest error. |
| 11: stale planning wording | CURRENT_STATE now consistently describes HI-S003 as admitted in REQ-024 and pending external review at req_impl. |
| 12: CA dependency bound/identity | certifi has a reviewed >=2024.8.30,<2027 window. Installed smoke records its version and SHA256 of the actual CA bundle. All builder resolution/install paths use that bound. |
| 13: openssl prerequisite | Kept hard failure rather than skipping required TLS tests. README explicitly identifies openssl on PATH for source TLS tests and retained REST artifact smoke; the installed REQ-024 ws:// profile itself does not invoke openssl. |
| 14: authority spelling | Specification now says the accepted configuration normalizes the hostname to lowercase while preserving explicit port spelling; ws/wss derivation reuses that normalized root. |

## Evidence integrity limits

Official release metadata is linked in the machine audit:
[h11](https://pypi.org/pypi/h11/0.16.0/json),
[anyio](https://pypi.org/pypi/anyio/4.15.1/json),
[certifi](https://pypi.org/pypi/certifi/2026.7.22/json).
The initial REQ-024 dependency hashes match those releases. The historical
REQ-023 hashes do not match wheel or sdist digests. A new successful execution
cannot certify the original dependency bytes. BUG-032 remains an explicitly
open historical-evidence follow-up; no root cause, original reproduction,
production incident or unrelated runtime remediation is invented.
