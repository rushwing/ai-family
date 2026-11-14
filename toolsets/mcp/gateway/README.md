# toolsets/mcp/gateway —— MCP 网关（信任边界）

请求验签 · 工具白名单 · 工具侧 JWT 校验 · write 类 risk 两段式 · 审计（ADR-010）。
所有工具调用唯一入口；确认令牌仅来自 ChatUI 用户点击、网关校验来源，Agent/Planner 不能自我确认。

## M1（REQ-003 WP-4）已落地

入口 `gateway.app:app`（FastAPI）。`/tools/{tool}` 单一入口执行：

1. **工具侧 OIDC JWT 验签**（缺 / 非 JWT / 篡改 → 401；旧 `X-Telegram-Chat-Id` header 非 JWT → 401）
2. **manifest 角色门禁**（取自 `goal_mcp` 契约；kid 不得写 create/approve 等 → 403）
3. **tenant scope**：body 显式 `family_member_id` ≠ 调用者 → 跨成员越权 403 + 审计
4. **write 类两段式**：普通 `/tools/{tool}` bearer 通道不能签发确认；只有持有独立
   `AIFAMILY_CONFIRMATION_SECRET` 的 ChatUI/BFF 用户交互通道，才能向 `/confirmations/{tool}`
   提交 HMAC 证明并取得 confirm token。证明绑定时间戳、一次性 nonce、OIDC session、成员、
   工具和 payload；execute 还须带网关签发、**会话+成员+工具+payload 绑定、一次性** token
5. **旧直连禁用**：GoalAgent 自身的 `/api/v1/*` 与 `/mcp/*` 默认返回 410；仅配置的内部网关令牌可进入
6. **审计**：deny/allow 均记录；admin 可查全量，adult/kid 只能查本人记录

工具的**功能分发**经 `create_app(executor=...)` 注入；真实分发到 goal-mcp FastMCP 随服务联调
在 req_impl_review 闭环。未注入 executor 的默认应用对工具请求返回 503，并在 `/readyz` 报未就绪，
不会伪造成功。内存 confirm/audit 仅用于单实例边界验证，已有 TTL/容量限制。
共享 PG confirm 增量与 home 注册边界已由 human-001 接受并合并至 PR #80；持久化 audit 仍是联调项。

## 测试与联调

```bash
# 无外部服务的 manifest / trust-boundary 回归
cd toolsets/mcp/gateway && pip install -e ../goal-mcp -e .[test]
pytest ../goal-mcp/tests tests -q

# 完整 TC-003-04B / TC-003-02B 还需 Keycloak 与已注入真实 executor 的应用实例
export AIFAMILY_OIDC_ISSUER=http://localhost:8081/realms/ai-family
export AIFAMILY_OIDC_AUD=ai-family-chatui
export AIFAMILY_GATEWAY_URL=http://localhost:8080
export AIFAMILY_CONFIRMATION_SECRET='32-byte-or-longer-shared-chatui-bff-secret'
python -m pytest tests/ ../../../tests -q -k "goal_write_boundary or goal_jwt_boundary"
```

模块级 `gateway.app:app` 故意不带 executor，只用于验证 fail-closed/readiness，不可作为完整联调实例。
未设 `AIFAMILY_GATEWAY_URL` 时外部服务用例 skip（两段式评审：tc_impl 审代码名副其实，
真实 executor + Keycloak 真跑归 req_impl_review）。

## REQ-003/004 accepted shared prerequisite increment

[Human bounded acceptance](../../../harness/tasks/evidence/REQ-003-004-pr80-acceptance.md)
records PR #80, merged as `9315763` on 2026-11-14, all pre-review dispositions
and source-specific PG16 verification. Full REQ-003/004 completion, the
REQ-039 production guard and physical dispatch remain separate. Human-001
has since authorized REQ-039 T17/design refinement; read the current design
and handoff in [REQ-039](../../../harness/tasks/features/REQ-039.md). No guard
runtime was delivered by the initial design-only change; the later combined
implementation is described below and remains pending external review.

`gateway.persistence.PostgresConfirmStore` extends the shared `confirm_token`
platform table through migration `0006_gateway_confirmation.sql`. Apply migrations
0001–0006 with the migration role before enabling this backend. Existing kid
check-in records keep their original protocol (`gateway_version IS NULL`).
Gateway rows are version 1, store a SHA-256 token digest, session, member, tool,
payload digest, database expiry and consumption time. Raw tokens/payloads are
not persisted. Proof nonce claim and token issuance share one transaction;
consumption is a conditional UPDATE with one winner. Connections use
transaction-local aifam_app/member scope, five-second connection/statement/lock
bounds and no retries or memory fallback on error.

Configure `AIFAMILY_GATEWAY_PG_DSN` separately from the BFF-held
`AIFAMILY_CONFIRMATION_SECRET`, or inject a `PostgresConfirmStore` into
`create_app(confirmation_store=...)`. These are private server configuration,
never Agent inputs. The connection principal must be allowed to SET ROLE
`aifam_app`, with no untrusted SQL interface. The default Goal-only boundary
mode still uses the bounded process-local store if no database is configured;
it cannot enable the registered home write tool. A configured but unavailable
backend returns `confirmation_unavailable` (503), never local success.

`home.execute_action` is registered with admin/adult roles, user-source
confirmation and TC-004-02 metadata. Both issuance and execution remain 503
until a durable backend **and** an `AuthenticatedTool` are injected. A generic
Goal executor cannot handle that name. The wrapper rechecks the original JWT,
member/role and a required current-resource policy, and passes a fresh
transaction-local member-scoped PG connection to its trusted handler. Metadata,
claims and parameters are detached. The policy must implement the later
REQ-039 canonical validation, current availability and home/device grants;
no such production guard or home handler is included here. The wrapper is an
internal tool implementation, never a separate public route bypassing the
gateway's confirmation check. Do not expose its callable as another endpoint.
Applying the wrapper to all Goal runtime handlers remains REQ-003/004 closeout.

The JWT/policy preflight runs before the handler transaction. RLS isolates
members; it does not serialize changes to home/device grants. A production
handler MUST recheck mutable grants, device binding and current availability
on the supplied connection before recording an authorized write/task intent.
Lock the authoritative grant/binding rows (for example SELECT ... FOR SHARE)
until that transaction commits; revocation writers must update those same
rows, or use an equivalent shared version/locking protocol. A second unlocked
policy read does not close the race. Missing transactional policy composition
must keep production home execution unavailable. The REQ-039 design handoff
must specify this protocol and test concurrent revocation. A fixture regression
here revokes a grant after preflight and demonstrates a handler-side locked
recheck denying execution. It is not production guard certification.
Handler ToolDenied/ToolUnavailable failures preserve redacted 403/503 responses
and roll back that handler transaction; unexpected failures become fixed 503.

A valid HMAC signature is necessary before the gateway calls `issue_confirmed`.
That low-level method is trusted composition, not a public issuance route.
The database independently rechecks proof age and persists the nonce claim until its safe operator retention expiry;
restarted processes and other gateway instances cannot mint another token from
that proof. Nonce capacity is never evicted to admit a replay. An operator may
clean expired token rows and nonce claims only after their full acceptance
window (including allowed future clock skew) has passed; runtime aifam_app has
no nonce DELETE/UPDATE grant. Keep instance clocks synchronized. Nonces must be
random and globally unique across the shared BFF channel.

Retention runbook: retain nonce claims for at least 24 hours from database
claimed_at. This exceeds twice the store's enforced maximum proof age of 3600
seconds (a future-dated proof can remain acceptable after its initial claim).
Run maintenance daily as a separate operator/migration principal, with alerts
on oldest eligible row age, retained row count and database capacity. Pause
confirmation issuance on every instance and drain in-flight issuance
transactions before pruning; use database time, never a host clock. In bounded
batches, delete nonce rows with claimed_at < clock_timestamp() - interval
'24 hours', then resume issuance. Expired version-1 token rows may be pruned
separately using database expiry; never delete legacy check-in rows as part
of this job. At larger volumes index claimed_at before scheduling cleanup.
The application role must retain no nonce UPDATE/DELETE privilege. If clock
integrity, maximum proof age or draining cannot be established, retain claims
and suspend issuance on capacity pressure; never evict live claims. No operator
job or scheduler is installed by this increment.

Once consumed, a token stays consumed even if the handler fails or the process
crashes. Retry requires a new user confirmation. The caller must show that the
attempt failed and request a fresh explicit confirmation; it must not silently
retry the consumed token or automatically mint another approval. A lost response
has an unknown outcome: reconcile through the future governed task/idempotency
contract before offering another write, because re-confirmation alone does not
prevent duplicate effects. This does not implement durable
task idempotency, provider delivery, physical convergence or durable audit;
those gates still precede physical integration. Roll back by disabling the home
handler/database configuration, retaining new columns/tables and replay records;
do not delete live confirmation state or restore a process-memory write path.

Run the dedicated real-PostgreSQL tests with a disposable administrator DSN:

```bash
AIFAMILY_CONFIRMATION_TEST_DSN='<private disposable PG DSN>' \
AIFAMILY_REQUIRE_CONFIRMATION_PG=1 \
python -m pytest toolsets/mcp/goal-mcp/tests toolsets/mcp/gateway/tests -q \
  --junitxml=/tmp/mcp-boundary-results.xml
python tools/check_gateway_results.py /tmp/mcp-boundary-results.xml
```

The fixture creates/drops a random test database, applies all migrations twice,
and tests actual RLS, atomic proof claims, concurrent consumption, independent
processes, rollback and authenticated HTTP composition. CI provides PG16 and
requires every case identity in tools/gateway_required_cases.json exactly once
and passing. The manifest retains all original 51 case identities plus the
pre-review regressions; missing, renamed, duplicated, skipped or failing cases
fail the gate. New required cases must be explicitly added to that manifest;
changing it triggers MCP CI. Historical provenance remains an immutable record
of the earlier run, rather than the live acceptance manifest. Legacy
external Goal/IdP cases still report their own environment skips and are not
relabeled as new prerequisite evidence. Fixture RS256 verification is distinct
from live IdP certification. `/healthz` reports configured durable/home wiring;
these flags describe configuration, not a passing persistence health probe.

## REQ-039 shared home guard (pending external review)

`gateway.home_guard.HomeActionGuard` assesses the original bearer and an exact
raw canonical ActionRequest, with server-owned inventory/bindings/descriptors,
a selected provider alias/configuration generation, authority, CurrentStateStore,
UTC clock and mandatory max_availability_age_ms. Configure a 1–300000 ms age
budget and finite 1–5 second resource wait. `assess()` exports only
status/reason: eligibility is not a permission token and consumes no confirmation.
`as_tool()` supplies the authenticated registered wrapper for existing gateway
composition with PostgresConfirmStore and the independent BFF secret. The
default application still has no home guard/handler and stays unavailable.

Only exact single_store_v1 authority composition tied to that store is supported.
The trusted authority's lease holds real PG grant/binding/generation locks on
the supplied member-scoped connection; its revokers/rebind writers must use the
same rows. The guard then takes `CurrentStateStore.capture_lease()` v1, holding
the existing publication lock used by put/apply/rebuild/reconcile/stale/epoch
writers. All capture access expires at exit. Acquire DB before state, never
reverse that order; release state before ending the DB transaction. Existing
read/snapshot calls alone do not satisfy this retained barrier. No production
policy adapter/table or distributed state fence is supplied. Fixture adapters
are test-only; unsupported distributed composition is unavailable.

Pre-grant unknown/ungranted targets return forbidden without descriptive lookup.
An existing grant contradicting the configured inventory/generation is
guard_unavailable. Capability/action/argument failures become visible only
after exact grants; unknown_home/unknown_device never escape as guard reasons.
The exact reason vocabulary is specified in REQ-039. Availability must be online,
fresh in the current committed epoch, not invalidated by reconnect, and within
its own observation-age budget. Recent unrelated properties do not refresh it.
Future observations deny; trusted clock regression/failure is unavailable.

Both confirmation issuance and execution run fresh preflight. Final tool entry
rechecks identity/grants/configuration/semantics/availability under the retained
lease after durable token consumption. There is no executor/task sink option:
even eligible confirmed requests return fixed 503 while physical execution is
absent, never a fabricated accepted task or success. Final failures keep the
confirmation consumed and roll back the handler transaction. No guarded
provider call, durable audit or task idempotency is claimed.

CI pins the original 63 prerequisite identities plus 86 guard cases, checks
strict guard/fabric types and the complete source regressions, and builds
direct and sdist-derived schema/fabric/goal/gateway wheels. Four fresh-venv
installed PG smokes run outside the checkout with -I, both ordinary and -O.
Run `tests/build_guard_artifacts.py --out-dir <outside-checkout-dir>` with a
dedicated AIFAMILY_CONFIRMATION_TEST_DSN and build/hatchling/pip installed.
The script downloads dependency wheels once, installs them offline into each
smoke environment and records artifact hashes. Tests create/drop random test
databases; fixture RS256/JWKS substitution is not live IdP certification.
