# REQ-039 / HI-S022 prerequisite inspection

[planner-001][2026-11-14] Source inspected: merged main
`fec13be` (REQ-038 housekeeping PR #79), on Linux aarch64.
GitHub readback confirms PR #79 merged at 2026-11-11T11:42:56Z; PR #78's
implementation acceptance is recorded in the REQ-038 closeout.
This is a source inspection, not independent TC approval or runtime acceptance.

## Shared confirmation persistence is unavailable

- [ConfirmStore](../../../toolsets/mcp/gateway/gateway/confirm.py) uses a
  per-instance dictionary and threading lock. Its module explicitly defers PG
  persistence. Session/member/tool/payload binding, TTL and local single-use
  behavior do not establish restart or multiple-instance guarantees.
- [InteractionVerifier](../../../toolsets/mcp/gateway/gateway/interaction.py)
  tracks signed-proof nonces in another process-local dictionary. Another
  instance or a restart has no shared replay record; a still-fresh signed proof
  can reach token issuance again. Durable token storage alone is insufficient.
- [Gateway app](../../../toolsets/mcp/gateway/gateway/app.py) constructs both
  stores internally for each app. No durable-store injection or PG transaction
  is wired into issuance/consumption. Audit also uses a bounded in-memory deque.
- [Migration 0002](../../../data/migrations/0002_goalagent_slice.sql) creates
  confirm_token; [0005](../../../data/migrations/0005_confirm_token_checkin.sql)
  adds task/consumption fields for check-in. DDL existence does not implement
  the gateway's exact bound-payload, durable atomic confirmation protocol.

## Registered home-tool boundary is unavailable

The gateway imports [goal_mcp.tool_registry](../../../toolsets/mcp/goal-mcp/goal_mcp/manifest.py),
a fixed 36-tool Goal registry. It has no registered Home Intelligence action
guard/tool. Functional execution is an injected callback; the default app
returns executor_unavailable. Existing registration checks are useful shared
work but do not establish a governed home-action entry point or device policy.

[REQ-003](../features/REQ-003.md) remains req_impl_review / evaluator-001;
[REQ-004](../features/REQ-004.md) remains draft / unassigned.
[TC-003-04](../test-cases/TC-003-04.md) is implemented, not passing, and specifies
Goal tools. Its external tests require a gateway, IdP and confirmation channel;
it supplies no executed durable home-tool evidence. Their owners and scope
remain unchanged.

## Executed checks and limits

A local attempt using CPython 3.12.12 to run
`test_gateway_unit.py` and `test_goal_manifest.py` together stopped during
collection: the existing `.venv` lacks `jwt` (PyJWT). No test pass or skip count
is claimed for that failed run. A direct package import using system Python
also stopped because FastAPI is absent. No dependency installation, shared
runtime modification, external service test, database test, live IdP/HA test,
concurrency experiment or restart experiment was performed. These unavailable
executions do not weaken the source-level evidence of process-local storage.

Admission verification runs governance/planning and navigation checks only;
results are recorded below after execution. No new guard TC is created while
blocked, and AC1–AC4 remain unchecked.

## Disposition

The source Story requires remaining blocked if verified shared persistence is
unavailable. [REQ-039](../features/REQ-039.md) records T16 and concrete unblock
conditions. Runtime integration stops here. Reuse the shared implementation
once its owner supplies exact-commit passing evidence; do not introduce a
second confirmation store or enable physical writes under this admission.

Admission checks passed on 2026-11-14: `bash scripts/check.sh` (all governance
checks, all 21 planning regressions and fabric CI wiring), public-data scan,
all 18 new REQ/evidence local Markdown targets and `git diff --check`.
The isolated planning fixture now includes REQ-039 and its shared REQ-003/004
dependencies; the first run exposed those missing fixture dependencies, which
were added before the passing rerun. Runtime modules and runtime tests remain
unchanged. These checks verify the admission packet, not guard acceptance.
