# REQ-031 local pre-review findings F1/F2

[generator-001][2026-10-19] Human-001 supplied a local pre-review explicitly
without independent lifecycle signatures and instructed “Fix all findings”.
Source commit `16d0fe4` addresses both findings. O1 describes the reviewer's
Termux environment reset and requires no repository change.

F1: four deterministic cases now reject duplicate envelope IDs, envelope success
fields, record IDs and nested state attributes. Each frame is otherwise valid
under last-wins decoding, avoiding the older malformed-envelope case's masking
effect. They check finite diagnostics, completed labels, no later commands,
single connection cleanup and privacy. Removing the `_pairs` duplicate-key check
makes all four fail with `DID NOT RAISE HADiscoveryError`.

F2: retain the final closed guard and explain that the owned worker's cancellation
path normally prevents publication. A new event-controlled test pauses cleanup
after all four reads succeed, calls aclose, then releases cleanup. Discovery must
raise CancelledError, close must finish, and no owned tasks or snapshot may remain.
Ignoring cancellation observed during cleanup makes this test fail with
client_closed instead of CancelledError. Removing only the defensive closed
guard is not claimed to be a behavioral mutation killed by this test.

## Validation

- Full required fabric suite: **1419 passed**, zero skips, in 63.55 seconds.
- Full required shared suite: **1795 passed**, zero skips.
- **113 discovery cases**; TC-031-01/02/03/04 groups: **20 / 73 / 31 / 12**.
- Five new cases pass; two targeted mutations fail by assertions (four duplicate
  key failures and one cleanup cancellation failure), not by timeout.
- Ruff, strict mypy (16 runtime sources), all nine governance/requirements
  scripts, 21 planning regressions, secret scan and whitespace checks pass.
- CI keeps all twelve required-runtime flags and raises the installed-artifact
  expected fabric count from 1414 to **1419**.

[Follow-up provenance](REQ-031-review-fixes-provenance.json) retains exact tested
source, JUnit/log hashes, totals and reproducible mutation harness/outcomes. Local
execution uses Linux aarch64 / Python 3.12.12. An initial sandboxed discovery run
passed 112 cases but could not bind the loopback socket; the authorized full run
outside the sandbox passed all cases. Historical [implementation evidence](REQ-031-runtime-implementation.md)
and [artifact provenance](REQ-031-artifact-provenance.json) retain their original
source/counts; they do not describe the amended source. Fresh wheel-pair and
Python 3.13/3.14 validation belongs to the final PR CI matrix.

Runtime executable behavior is unchanged: its only edit is the F2 comment.
Accepted modules, shared contracts and original provenance remain unchanged.
[REQ-031](../archive/done/features/REQ-031.md) remains req_impl / generator-001, review_round 0,
with unchecked ACs, implemented TCs and [draft PR #63](https://github.com/rushwing/ai-family/pull/63).
This response is not independent approval, human acceptance or merge authority.
