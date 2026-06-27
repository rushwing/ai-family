"""TC-003-07（B）：kid M1 结构化只路径与越界转家长（agent 侧）。

需求 7 / 验收 #1·#6；回归 BUG-012。

env-gated：kid 结构化路径 enforcement（WP-7）尚未落地时 skip；
req_impl 接 RLS 只读 + Draft-First + 模板赞语后转 passing。
"""
import os
from pathlib import Path

import pytest

DSN = os.getenv("AIFAMILY_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="设 AIFAMILY_PG_DSN 运行 kid 结构化路径用例")

kid = pytest.importorskip("app.services.kid_path", reason="kid 结构化路径未落地（WP-7）")
praise = pytest.importorskip("app.services.praise_engine")


@pytest.fixture(scope="module", autouse=True)
def _seed():
    """应用迁移 + 种数据：kid 一条目标链（target→plan→milestone→task）+ adult 一个目标（跨成员隔离）。"""
    psycopg = pytest.importorskip("psycopg")
    repo = Path(__file__).resolve().parents[4]
    with psycopg.connect(DSN, autocommit=True) as admin:
        for f in sorted((repo / "data" / "migrations").glob("*.sql")):
            admin.execute(f.read_text(encoding="utf-8"))
        for tbl in ("check_in", "task", "weekly_milestone", "plan", "target"):
            admin.execute(f"DELETE FROM {tbl} WHERE family_member_id IN ('kid','adult')")
        admin.execute("DELETE FROM audit.event WHERE family_member_id IN ('kid','adult','A','B')")
        tid = admin.execute(
            "INSERT INTO target (family_member_id, title) VALUES ('kid','Kid Goal') RETURNING id"
        ).fetchone()[0]
        pid = admin.execute(
            "INSERT INTO plan (family_member_id, target_id, title) VALUES ('kid',%s,'P') RETURNING id",
            (tid,),
        ).fetchone()[0]
        mid = admin.execute(
            "INSERT INTO weekly_milestone (family_member_id, plan_id, title) VALUES ('kid',%s,'M') "
            "RETURNING id", (pid,),
        ).fetchone()[0]
        admin.execute(
            "INSERT INTO task (family_member_id, milestone_id, title) VALUES ('kid',%s,'T')", (mid,)
        )
        admin.execute("INSERT INTO target (family_member_id, title) VALUES ('adult','Adult Goal')")
    yield


@pytest.fixture
def llm_spy(monkeypatch):
    """可观测 LLM spy：断言 kid 流程不产生自由生成调用。"""
    calls = []
    monkeypatch.setattr(kid, "_llm_complete", lambda *a, **k: calls.append(k))
    return calls


def test_kid_can_read_own_goal_and_draft_first_checkin(llm_spy):
    goals = kid.list_goals(member="kid")
    assert all(g.family_member_id == "kid" for g in goals)
    result = kid.submit_checkin(member="kid", task_id=goals[0].tasks[0].id, draft_first=True)
    assert result.accepted
    assert llm_spy == [], "kid 打卡不得调用 LLM 自由生成"


def test_kid_cannot_view_other_member_goal():
    assert kid.list_goals(member="kid", owner="adult") == []


@pytest.mark.parametrize("action", ["create_goal", "approve_plan", "write_platform", "free_chat"])
def test_kid_disallowed_actions_redirect_to_parent(action, llm_spy):
    with pytest.raises(kid.RedirectToParent):
        kid.dispatch(member="kid", action=action, payload={})
    # 越界不得产生目标写入、不得调用 LLM
    assert kid.goal_write_count(member="kid") == 0
    assert llm_spy == []


def test_kid_praise_is_offline_template(llm_spy):
    msg = praise.praise(member="kid", streak=3)
    assert praise.is_template(msg), "赞语须来自离线模板，不走 LLM"
    assert llm_spy == []


def test_deny_and_allow_are_audited():
    kid.submit_checkin(member="kid", task_id=kid.list_goals(member="kid")[0].tasks[0].id)
    with pytest.raises(kid.RedirectToParent):
        kid.dispatch(member="kid", action="create_goal", payload={})
    events = kid.recent_audit(member="kid")
    assert any(e.action == "checkin" and e.result == "allow" for e in events)
    assert any(e.action == "create_goal" and e.result == "deny" for e in events)
