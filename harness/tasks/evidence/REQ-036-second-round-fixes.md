# REQ-036 second-round pre-review repairs

Historical implementation/review record. The later human final disposition in
[final acceptance](REQ-036-review-acceptance.md) supersedes pending approval
and req_impl stopping statements below; source-specific evidence remains historical.

On 2026-11-10 human-001 supplied the second-round local pre-review of
[PR #74](https://github.com/rushwing/ai-family/pull/74) at
`3826e87a25dbadae235663c53d61d9d07316d817` and instructed “fix all findings”.
The report confirms T1/F1–F6 are repaired and identifies no new functional
defect. It explicitly disclaims independent approval. The instruction extends
generator repair work within `req_impl / generator-001`; AC1–AC5 remain
unchecked, all four TC proposals remain draft, and the PR remains draft.

## Disposition

| Item | Action |
| --- | --- |
| Result copy/deepcopy coverage | Extend the existing success/failure serialization regression to exercise both `copy.copy` and `copy.deepcopy`, requiring the same fixed TypeError as pickle. Keep detached JSON export and caller-mutation checks. Update draft TC-036-04 accordingly. |
| Independent TC review and implementation acceptance | Preserve the [independent review handoff](REQ-036-review-handoff.md). Generator execution records cannot approve the four criteria or their mappings. No independent signature or lifecycle promotion is asserted. |
| Historical provenance | Preserve initial provenance for `449aa337`, repair provenance for `07796cc3`, and the six historical mutation records unchanged. Runtime bytes remain unchanged; this follow-up changes regression test bytes, so those historical records are not represented as new test-source provenance. |
| Reviewer editable-install mismatch | The reviewer disclosed and corrected their own stale import path. It requires no repository repair. Verification here checks the imported runtime path against this checkout. |

The added assertions verify existing copy behavior; they require no runtime
change and add no parametrized cases. The fabric suite still expects 1,960
cases and TC mappings remain 11/6/38/17. The mapping counts can overlap and are
not independent acceptance counts. Existing installed smoke remains 18 checks.

## Verification

On 2026-11-10, Linux aarch64 / CPython 3.12.12, the full suite passed
**1,960 cases, zero failures/errors/skips**, with all sixteen required-runtime
flags (84.07 seconds). The targeted reconciliation suite passed 64 cases.
Ruff, strict mypy on twenty runtime modules, governance and all 21 planning
regressions passed. The full suite includes the installed-smoke contract probe.
The authorized full run used local loopback sockets outside the sandbox.

[Verification metadata](REQ-036-second-round-verification.json) records the
exact runtime/test/TC hashes, JUnit digest and unchanged 11/6/38/17 TC mappings.
It explicitly identifies the dirty base and tested follow-up bytes; it is not
a new clean-commit artifact or mutation attestation. Current-head CI supplies
separate installed-artifact and Python matrix evidence after push.
