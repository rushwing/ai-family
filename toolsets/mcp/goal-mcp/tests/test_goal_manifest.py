"""TC-003-04（A）：36 个 Goal MCP tool 的 manifest 契约与注册门禁。

需求 4 / 验收 #3；回归 BUG-017。

依赖 goal-mcp 包（WP-4）落地；未就绪时整模块 skip。该目录随 REQ-005 workspace 接 CI。

BUG-031 修复：不再只数总数；固化逐 tool 名称 + risk/roles/tenant_scope 契约，
覆盖「写工具被误标为 read」「confirm token 用户来源绑定」「kid 越权写」。

契约来源：goal-agent 现有 37 个 @mcp.tool，按 docs/design/08 defer（wizard research/
feasibility 节点 M1 移除）去掉 get_wizard_sources → M1 = 36 个。
"""
import pytest

goal_mcp = pytest.importorskip("goal_mcp", reason="goal-mcp 包未落地（WP-4）")

R, W = "read", "write"
# 角色集（系统真值：goal-agent best_pal→admin / go_getter→adult·kid；REQ-003 acceptance 与
# docs/design/08 §6 明定写目标为 admin/adult。kid 走结构化只路径：读 + checkin，不写目标/计划）。
ADM_AD = frozenset({"admin", "adult"})         # 写：家长 + 成人 go_getter
ALL3 = frozenset({"admin", "adult", "kid"})    # 读：含 kid 只读自有
# name -> (risk, roles, tenant_scope)
EXPECTED: dict[str, tuple[str, frozenset, str]] = {
    # admin_tools —— 仅 admin（成员管理），平台/共享 scope
    "add_go_getter": (W, frozenset({"admin"}), "shared"),
    "update_go_getter": (W, frozenset({"admin"}), "shared"),
    "remove_go_getter": (W, frozenset({"admin"}), "shared"),
    "list_go_getters": (R, frozenset({"admin"}), "shared"),
    "add_best_pal": (W, frozenset({"admin"}), "shared"),
    "update_best_pal": (W, frozenset({"admin"}), "shared"),
    "remove_best_pal": (W, frozenset({"admin"}), "shared"),
    "list_best_pals": (R, frozenset({"admin"}), "shared"),
    # checkin_tools —— 读全角色；写含 kid（Draft-First 打卡），成员 scope
    "list_today_tasks": (R, ALL3, "member"),
    "list_week_tasks": (R, ALL3, "member"),
    "checkin_task": (W, ALL3, "member"),
    "skip_task": (W, ALL3, "member"),
    "get_go_getter_progress": (R, ALL3, "member"),
    # plan_tools —— 写 admin+adult，读全角色（kid 只读自有）
    "create_target": (W, ADM_AD, "member"),
    "update_target": (W, ADM_AD, "member"),
    "delete_target": (W, ADM_AD, "member"),
    "list_targets": (R, ALL3, "member"),
    "generate_plan": (W, ADM_AD, "member"),
    "update_plan": (W, ADM_AD, "member"),
    "cancel_plan": (W, ADM_AD, "member"),
    "list_plans": (R, ALL3, "member"),
    "get_plan_detail": (R, ALL3, "member"),
    # report_tools —— 写 admin+adult（kid 不生成），读全角色
    "generate_daily_report": (W, ADM_AD, "member"),
    "generate_weekly_report": (W, ADM_AD, "member"),
    "generate_monthly_report": (W, ADM_AD, "member"),
    "list_reports": (R, ALL3, "member"),
    # tracks_tools —— 目录，读，全角色，共享
    "list_track_categories": (R, ALL3, "shared"),
    "list_track_subcategories": (R, ALL3, "shared"),
    # wizard_tools（M1 去掉 get_wizard_sources）—— 写 admin+adult
    "start_goal_group_wizard": (W, ADM_AD, "member"),
    "get_wizard_status": (R, ADM_AD, "member"),
    "set_wizard_scope": (W, ADM_AD, "member"),
    "set_wizard_targets": (W, ADM_AD, "member"),
    "set_wizard_constraints": (W, ADM_AD, "member"),
    "adjust_wizard": (W, ADM_AD, "member"),
    "confirm_goal_group": (W, ADM_AD, "member"),
    "cancel_goal_group_wizard": (W, ADM_AD, "member"),
}
WRITE_TOOLS = {n for n, (risk, *_ ) in EXPECTED.items() if risk == W}
KID_ALLOWED = {n for n, (_, roles, _) in EXPECTED.items() if "kid" in roles}


def _registry():
    return goal_mcp.tool_registry()


def _by_name():
    return {t.name: t for t in _registry().list_tools()}


def test_exact_36_tool_names_registered():
    names = set(_by_name())
    assert names == set(EXPECTED), (
        f"工具集与契约不符：缺 {set(EXPECTED) - names}，多 {names - set(EXPECTED)}"
    )


def test_m1_deferred_tool_not_registered():
    assert "get_wizard_sources" not in _by_name(), "M1 已移除 wizard research/feasibility（08 defer）"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_tool_risk_roles_scope_match_contract(name):
    tool = _by_name()[name]
    risk, roles, scope = EXPECTED[name]
    assert tool.risk == risk, f"{name} risk 应为 {risk}（防写工具被误标为 read）"
    assert frozenset(tool.manifest["roles"]) == roles, f"{name} 角色契约不符"
    assert tool.manifest["tenant_scope"] == scope, f"{name} tenant scope 契约不符"


@pytest.mark.parametrize("name", sorted(WRITE_TOOLS))
def test_write_tools_two_phase_and_user_sourced_confirm(name):
    m = _by_name()[name].manifest
    assert m["two_phase"] is True, f"{name} write 类须两段式"
    assert m["confirm_source"] == "user", f"{name} confirm token 须用户来源绑定（非 Agent 自生成）"
    assert m.get("auth") and m.get("test_ref"), f"{name} 须有 auth + test_ref"


def test_kid_cannot_write_create_or_approve():
    by = _by_name()
    for forbidden in ("create_target", "generate_plan", "confirm_goal_group", "delete_target"):
        assert "kid" not in by[forbidden].manifest["roles"], f"kid 不得写 {forbidden}"
    assert KID_ALLOWED  # kid 仍可走只读 + checkin


def test_write_tool_mislabeled_as_read_rejected():
    with pytest.raises(goal_mcp.RegistrationError):
        _registry().register(goal_mcp.fixture_tool(name="bad_write", risk="read", mutates=True))


def test_tool_without_auth_or_test_ref_rejected():
    with pytest.raises(goal_mcp.RegistrationError):
        _registry().register(goal_mcp.fixture_tool(risk="write", auth=None))
    with pytest.raises(goal_mcp.RegistrationError):
        _registry().register(goal_mcp.fixture_tool(risk="write", test_ref=None))
