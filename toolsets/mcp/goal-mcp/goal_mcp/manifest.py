"""GoalAgent MCP tool manifest 契约与注册门禁 —— REQ-003 WP-4 / TC-003-04（A）。

需求 4 / 验收 #3；回归 BUG-017（write 类 tool 无 auth/无测试者拒绝注册）。

这里是 36 个 Goal MCP tool 的**逐 tool manifest 单一真值**（risk / 角色 / tenant scope /
两段式 / confirm 来源 / 工具侧 auth / 测试引用）。manifest 与 toolsets 网关、agent 侧
``app/auth/oidc.py`` 的 TOOL_POLICY 同源对齐（test_goal_manifest 的 EXPECTED 即本表）。

契约来源：goal-agent 现有 37 个 @mcp.tool，按 docs/design/08 defer（wizard research/
feasibility 节点 M1 移除）去掉 get_wizard_sources → M1 = 36 个。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

READ = "read"
WRITE = "write"

# —— 角色集（系统真值，与 08 §6 / REQ acceptance / oidc.TOOL_POLICY 对齐）——
ADMIN = frozenset({"admin"})                 # 仅家长管理员（成员管理）
ADM_AD = frozenset({"admin", "adult"})       # 写：家长 + 成人 go_getter
ALL3 = frozenset({"admin", "adult", "kid"})  # 读 / 打卡：含 kid 只读自有 + Draft-First

MEMBER = "member"
SHARED = "shared"

# name -> (group, risk, roles, tenant_scope)
# 6 组：admin(8) / checkin(5) / plan(9) / report(4) / tracks(2) / wizard(8) = 36
TOOL_SPEC: dict[str, tuple[str, str, frozenset, str]] = {
    # —— admin_tools：成员管理，仅 admin，平台/共享 scope ——
    "add_go_getter": ("admin", WRITE, ADMIN, SHARED),
    "update_go_getter": ("admin", WRITE, ADMIN, SHARED),
    "remove_go_getter": ("admin", WRITE, ADMIN, SHARED),
    "list_go_getters": ("admin", READ, ADMIN, SHARED),
    "add_best_pal": ("admin", WRITE, ADMIN, SHARED),
    "update_best_pal": ("admin", WRITE, ADMIN, SHARED),
    "remove_best_pal": ("admin", WRITE, ADMIN, SHARED),
    "list_best_pals": ("admin", READ, ADMIN, SHARED),
    # —— checkin_tools：读全角色；写含 kid（Draft-First 打卡），成员 scope ——
    "list_today_tasks": ("checkin", READ, ALL3, MEMBER),
    "list_week_tasks": ("checkin", READ, ALL3, MEMBER),
    "checkin_task": ("checkin", WRITE, ALL3, MEMBER),
    "skip_task": ("checkin", WRITE, ALL3, MEMBER),
    "get_go_getter_progress": ("checkin", READ, ALL3, MEMBER),
    # —— plan_tools：写 admin+adult，读全角色（kid 只读自有由 member scope + RLS 保证）——
    "create_target": ("plan", WRITE, ADM_AD, MEMBER),
    "update_target": ("plan", WRITE, ADM_AD, MEMBER),
    "delete_target": ("plan", WRITE, ADM_AD, MEMBER),
    "list_targets": ("plan", READ, ALL3, MEMBER),
    "generate_plan": ("plan", WRITE, ADM_AD, MEMBER),
    "update_plan": ("plan", WRITE, ADM_AD, MEMBER),
    "cancel_plan": ("plan", WRITE, ADM_AD, MEMBER),
    "list_plans": ("plan", READ, ALL3, MEMBER),
    "get_plan_detail": ("plan", READ, ALL3, MEMBER),
    # —— report_tools：写 admin+adult（kid 不生成），读全角色 ——
    "generate_daily_report": ("report", WRITE, ADM_AD, MEMBER),
    "generate_weekly_report": ("report", WRITE, ADM_AD, MEMBER),
    "generate_monthly_report": ("report", WRITE, ADM_AD, MEMBER),
    "list_reports": ("report", READ, ALL3, MEMBER),
    # —— tracks_tools：目录，读，全角色，共享 ——
    "list_track_categories": ("tracks", READ, ALL3, SHARED),
    "list_track_subcategories": ("tracks", READ, ALL3, SHARED),
    # —— wizard_tools（M1 去掉 get_wizard_sources）：写 admin+adult ——
    "start_goal_group_wizard": ("wizard", WRITE, ADM_AD, MEMBER),
    "get_wizard_status": ("wizard", READ, ADM_AD, MEMBER),
    "set_wizard_scope": ("wizard", WRITE, ADM_AD, MEMBER),
    "set_wizard_targets": ("wizard", WRITE, ADM_AD, MEMBER),
    "set_wizard_constraints": ("wizard", WRITE, ADM_AD, MEMBER),
    "adjust_wizard": ("wizard", WRITE, ADM_AD, MEMBER),
    "confirm_goal_group": ("wizard", WRITE, ADM_AD, MEMBER),
    "cancel_goal_group_wizard": ("wizard", WRITE, ADM_AD, MEMBER),
}

# M1 按 docs/design/08 defer 移除的 wizard research/feasibility 节点。
DEFERRED_TOOLS = frozenset({"get_wizard_sources"})

# 所有 write 类 tool 经网关时统一工具侧鉴权 + 两段式 + 用户来源 confirm。
_TOOL_AUTH = "oidc-jwt"
_WRITE_TEST_REF = "TC-003-04"   # 网关写边界 + manifest 契约
_READ_TEST_REF = "TC-003-02"    # 工具侧 JWT 边界（读）


class RegistrationError(Exception):
    """工具不满足 manifest 契约，拒绝注册（BUG-017：无 auth / 无测试 / 写误标 read）。"""


@dataclass(frozen=True)
class Tool:
    """一个已声明 manifest 的 MCP tool（注册门禁的最小单元）。"""

    name: str
    risk: str
    manifest: dict = field(default_factory=dict)

    @property
    def group(self) -> str:
        return self.manifest.get("group", "")

    @property
    def roles(self) -> frozenset:
        return frozenset(self.manifest.get("roles", ()))

    @property
    def tenant_scope(self) -> str:
        return self.manifest.get("tenant_scope", "")


class ToolRegistry:
    """工具注册表：注册即校验 manifest 契约，违反则 RegistrationError。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._validate(tool)
        if tool.name in self._tools:
            raise RegistrationError(f"工具重复注册：{tool.name}")
        self._tools[tool.name] = tool
        return tool

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    @staticmethod
    def _validate(tool: Tool) -> None:
        m = tool.manifest
        if tool.risk not in (READ, WRITE):
            raise RegistrationError(f"{tool.name} risk 非法：{tool.risk!r}")
        # 防「写工具被误标为 read」：mutates 与 risk 必须一致
        mutates = bool(m.get("mutates", tool.risk == WRITE))
        if mutates and tool.risk != WRITE:
            raise RegistrationError(f"{tool.name} 会写库但 risk 标为 read（误标）")
        if not m.get("roles"):
            raise RegistrationError(f"{tool.name} 缺角色契约")
        if m.get("tenant_scope") not in (MEMBER, SHARED):
            raise RegistrationError(f"{tool.name} tenant_scope 非法：{m.get('tenant_scope')!r}")
        # write 类：工具侧 auth + 测试引用 + 两段式 + 用户来源 confirm（BUG-017）
        if tool.risk == WRITE:
            if not m.get("auth"):
                raise RegistrationError(f"{tool.name} 写类 tool 缺工具侧 auth")
            if not m.get("test_ref"):
                raise RegistrationError(f"{tool.name} 写类 tool 缺测试引用 test_ref")
            if m.get("two_phase") is not True:
                raise RegistrationError(f"{tool.name} 写类 tool 须两段式 two_phase")
            if m.get("confirm_source") != "user":
                raise RegistrationError(
                    f"{tool.name} 写类 confirm 须用户来源（非 Agent 自生成）"
                )


def _build_tool(name: str, group: str, risk: str, roles: Iterable[str], scope: str) -> Tool:
    is_write = risk == WRITE
    manifest = {
        "group": group,
        "roles": frozenset(roles),
        "tenant_scope": scope,
        "mutates": is_write,
        "two_phase": is_write,
        "confirm_source": "user" if is_write else None,
        "auth": _TOOL_AUTH,
        "test_ref": _WRITE_TEST_REF if is_write else _READ_TEST_REF,
    }
    return Tool(name=name, risk=risk, manifest=manifest)


def tool_registry() -> ToolRegistry:
    """构建并返回含 36 个 Goal MCP tool 的注册表（每次新建，注册即校验契约）。"""
    reg = ToolRegistry()
    for name, (group, risk, roles, scope) in TOOL_SPEC.items():
        reg.register(_build_tool(name, group, risk, roles, scope))
    return reg


def fixture_tool(
    *,
    name: str = "fixture_tool",
    risk: str = WRITE,
    mutates: bool | None = None,
    roles: Iterable[str] | None = None,
    tenant_scope: str = MEMBER,
    two_phase: bool | None = None,
    confirm_source: str | None = None,
    auth: str | None = _TOOL_AUTH,
    test_ref: str | None = _WRITE_TEST_REF,
) -> Tool:
    """构造用于注册门禁负例的工具（默认是「合法 write」，按需把某字段置空触发拒绝）。"""
    is_write = risk == WRITE
    if mutates is None:
        mutates = is_write
    if two_phase is None:
        two_phase = is_write
    if confirm_source is None and is_write:
        confirm_source = "user"
    if roles is None:
        roles = ADM_AD if is_write else ALL3
    manifest = {
        "group": "fixture",
        "roles": frozenset(roles),
        "tenant_scope": tenant_scope,
        "mutates": mutates,
        "two_phase": two_phase,
        "confirm_source": confirm_source,
        "auth": auth,
        "test_ref": test_ref,
    }
    return Tool(name=name, risk=risk, manifest=manifest)
