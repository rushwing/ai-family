"""TC-003-10：ai-family 首个 Goal 的 dogfooding 与周报真实进度。

需求 9 / 验收 #4。

env-gated：未设 AIFAMILY_PG_DSN / AIFAMILY_MINIO_URL 或 dogfood 导入器（WP-10）
尚未落地时 skip；req_impl 起全栈后转 passing。

BUG-031 修复：不再先写固定文字再断言其存在；改为从版本化 harness source 真实读取
M0–M5 与各 REQ 状态，比对导入内容/周报内容与 source；重导后同时比对 milestone 与
requirement 的去重结果。
"""
import os
import re
from pathlib import Path

import pytest

DSN = os.getenv("AIFAMILY_PG_DSN")
MINIO = os.getenv("AIFAMILY_MINIO_URL")
pytestmark = pytest.mark.skipif(
    not (DSN and MINIO), reason="设 AIFAMILY_PG_DSN + AIFAMILY_MINIO_URL 运行 dogfooding 用例"
)

dogfood = pytest.importorskip("app.services.dogfood_import", reason="dogfood 导入器未落地（WP-10）")
report = pytest.importorskip("app.services.report_service")

REPO = Path(__file__).resolve().parents[4]
GLOSSARY = REPO / "GLOSSARY.md"
FEATURES = REPO / "harness" / "tasks" / "features"
ARCHIVE_FEATURES = REPO / "harness" / "tasks" / "archive" / "done" / "features"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    out = {}
    for key in ("req_id", "status"):
        m = re.search(rf"^{key}:\s*(.+)$", text, re.M)
        if m:
            out[key] = m.group(1).strip().strip('"')
    return out


def _harness_reqs() -> dict[str, str]:
    """从版本化 harness 读取 {req_id: status}（features + 归档）。"""
    reqs = {}
    for d in (FEATURES, ARCHIVE_FEATURES):
        for p in sorted(d.glob("REQ-*.md")):
            fm = _frontmatter(p)
            if fm.get("req_id"):
                reqs[fm["req_id"]] = fm.get("status", "")
    return reqs


def _harness_milestones() -> set[str]:
    return set(re.findall(r"\bM[0-5]\b", GLOSSARY.read_text(encoding="utf-8")))


@pytest.fixture
def first_goal():
    return dogfood.import_repo_milestones(source="harness", member="best_pal")


def test_first_goal_matches_versioned_source(first_goal):
    assert first_goal.title == "ai-family 项目开发"
    assert first_goal.family_member_id == "best_pal"  # 成员归属正确

    src_milestones = _harness_milestones()
    assert {"M0", "M1", "M2", "M3", "M4", "M5"} <= src_milestones
    assert {m.code for m in first_goal.milestones} == src_milestones, "里程碑须与 GLOSSARY source 一致"

    src_reqs = _harness_reqs()
    imported = {r.req_id: r.status for r in first_goal.requirements}
    assert imported == src_reqs, "导入的 REQ 列表/状态须与 harness source 一致（非占位）"


def test_reimport_dedups_milestones_and_requirements(first_goal):
    again = dogfood.import_repo_milestones(source="harness", member="best_pal")
    assert again.goal_id == first_goal.goal_id
    assert len(again.milestones) == len(first_goal.milestones), "重导不得重复 milestone"
    assert len(again.requirements) == len(first_goal.requirements), "重导不得重复 requirement"


def test_weekly_report_reflects_real_repo_state_and_is_archived(first_goal):
    rep = report.generate_weekly(first_goal.goal_id)
    src_reqs = _harness_reqs()

    # 周报须反映 source 真实状态（如 REQ-002 done、REQ-003 当前态），而非注入的固定文字
    assert src_reqs.get("REQ-002") == "done"  # source 真值（防固定文字假绿）
    assert "REQ-002" in rep.content and "done" in rep.content
    assert "REQ-003" in rep.content and src_reqs["REQ-003"] in rep.content
    assert "TODO" not in rep.content and "占位" not in rep.content  # 非占位文本

    archived = report.read_archived(rep.archive_ref)
    assert archived == rep.content
    assert any(e.action == "report.generate" for e in report.audit_for(rep.archive_ref))
