"""TC-003-04（B）：MCP 网关写操作门禁——两段式确认 token 与直连封堵。

需求 4 / 验收 #3；回归 BUG-017。

env-gated：未设 AIFAMILY_GATEWAY_URL 时 skip；req_impl 起网关后转 passing。

BUG-031 修复：登录 helper 统一为 tests/helpers/oidc.login_role；OIDC 环境齐备时
helper 缺失应失败而非静默 skip。
"""
import os
import sys
import time
import uuid
from pathlib import Path

import jwt
import pytest

from gateway.interaction import sign_interaction

httpx = pytest.importorskip("httpx")

GATEWAY = os.getenv("AIFAMILY_GATEWAY_URL")
pytestmark = pytest.mark.skipif(not GATEWAY, reason="设 AIFAMILY_GATEWAY_URL 运行网关写边界用例")

_TESTS_DIR = Path(__file__).resolve().parents[4] / "tests"
if _TESTS_DIR.is_dir() and str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))


def _adult_token() -> str:
    if not os.getenv("AIFAMILY_OIDC_ISSUER"):
        pytest.skip("设 AIFAMILY_OIDC_ISSUER 取真实 token")
    from helpers.oidc import login_role  # 缺失 → ImportError 冒泡为失败

    return login_role(os.getenv("AIFAMILY_OIDC_ISSUER"), "adult")


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


def _user_confirm(token: str, tool: str, params: dict) -> str:
    secret = os.getenv("AIFAMILY_CONFIRMATION_SECRET")
    if not secret:
        pytest.skip("设 AIFAMILY_CONFIRMATION_SECRET 运行用户确认通道用例")
    claims = jwt.decode(token, options={"verify_signature": False})
    session = claims.get("sid") or claims.get("session_state")
    member = claims.get("family_member_id")
    if not session or not member:
        pytest.fail("联调 token 必须包含 session 与 family_member_id")
    timestamp = int(time.time())
    nonce = uuid.uuid4().hex
    signature = sign_interaction(
        secret,
        timestamp=timestamp,
        nonce=nonce,
        session=session,
        member=str(member),
        tool=tool,
        params=params,
    )
    response = httpx.post(
        f"{GATEWAY}/confirmations/{tool}",
        json=params,
        headers={
            **_hdr(token),
            "X-AI-Family-Interaction-Timestamp": str(timestamp),
            "X-AI-Family-Interaction-Nonce": nonce,
            "X-AI-Family-Interaction-Signature": signature,
        },
        timeout=10,
    )
    assert response.status_code == 200
    return response.json()["confirm_token"]


def test_two_phase_user_confirm_then_execute():
    token = _adult_token()
    confirm_token = _user_confirm(token, "create_target", {"title": "t"})
    exe = httpx.post(
        f"{GATEWAY}/tools/create_target",
        json={"confirm_token": confirm_token, "title": "t"},
        headers=_hdr(token), timeout=10,
    )
    assert exe.status_code == 200


def test_confirm_token_cannot_authorize_mutated_payload():
    token = _adult_token()
    confirm_token = _user_confirm(token, "create_target", {"title": "safe"})
    changed = httpx.post(
        f"{GATEWAY}/tools/create_target",
        json={"confirm_token": confirm_token, "title": "EVIL"},
        headers=_hdr(token), timeout=10,
    )
    assert changed.status_code in (400, 403)


@pytest.mark.parametrize("confirm", [None, "forged-token", "agent-self-generated"])
def test_missing_or_forged_confirm_rejected(confirm):
    token = _adult_token()
    body = {"title": "t"}
    if confirm is not None:
        body["confirm_token"] = confirm
    r = httpx.post(f"{GATEWAY}/tools/create_target", json=body, headers=_hdr(token), timeout=10)
    assert r.status_code in (400, 403), "缺/伪造/Agent 自生成 confirm 必须被拒"


def test_confirm_token_bound_to_issuing_member():
    """确认 token 与签发成员绑定：adult 取的 confirm 不能被 admin 复用。

    用两个**均有写权**的成员（adult 签发 / admin 兑付）验证——拒绝来自 token 成员绑定，
    而非 admin 无写权（admin/adult 同为写角色，见 manifest 契约）。
    """
    token_a = _adult_token()
    confirm_token = _user_confirm(token_a, "create_target", {"title": "t"})
    if not os.getenv("AIFAMILY_OIDC_ISSUER"):
        pytest.skip("设 AIFAMILY_OIDC_ISSUER 取第二成员 token")
    from helpers.oidc import login_role

    token_admin = login_role(os.getenv("AIFAMILY_OIDC_ISSUER"), "admin")
    r = httpx.post(
        f"{GATEWAY}/tools/create_target",
        json={"confirm_token": confirm_token, "title": "t"},
        headers=_hdr(token_admin), timeout=10,
    )
    assert r.status_code in (400, 403), "confirm token 须绑定签发用户，不可跨成员复用"


@pytest.mark.parametrize("path", ["/api/v1/targets", "/openclaw/create_target"])
def test_legacy_direct_paths_disabled(path):
    r = httpx.post(f"{GATEWAY}{path}", json={}, timeout=10)
    assert r.status_code == 410, f"M1 旧 REST/OpenClaw 直连应明确禁用：{path}"


def test_cross_member_write_rejected_and_audited():
    token = _adult_token()  # 成员 A
    r = httpx.post(
        f"{GATEWAY}/tools/create_target",
        json={"family_member_id": "B", "title": "spoof"},
        headers=_hdr(token), timeout=10,
    )
    assert r.status_code == 403
    audit = httpx.get(
        f"{GATEWAY}/audit/recent", params={"action": "create_target", "result": "deny"},
        headers=_hdr(token), timeout=10,
    )
    assert audit.status_code == 200 and audit.json(), "越权写须留审计记录"
