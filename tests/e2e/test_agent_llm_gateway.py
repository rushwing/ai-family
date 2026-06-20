"""TC-003-09：Agent 侧 LLM 网关纪律——egress 强制 / fail-closed / 真实 per-user 预算。

需求 4 / 验收 #3；回归 BUG-030。

**受控手工 E2E（automated: false）**：依赖受控真实厂商凭证 + 隔离测试租户，会产生真实
计费 completion，**默认不在 CI/普通 pytest 运行**。须显式 opt-in：
    AIFAMILY_REAL_GATEWAY_TC=1 ./scripts/run_req003_real_gateway_tc.sh

BUG-031 修复：
- 用 master key 在隔离租户创建两个**确定性小额度**虚拟 key（用后删除清理），
  不再循环最多 50 次真实 completion。
- 断言三家真实 provider 各自成功 completion（不只 deepseek）。
- 小额度使**有界**次数内触发明确 429；并断言 A/B 计量相互独立。
- 输出脱敏证据（key 不入日志）。
"""
import os

import pytest

from conftest import require

httpx = pytest.importorskip("httpx")

pytestmark = pytest.mark.skipif(
    os.getenv("AIFAMILY_REAL_GATEWAY_TC") != "1",
    reason="受控手工用例：设 AIFAMILY_REAL_GATEWAY_TC=1 + 真实凭证显式运行（BUG-030）",
)

AGENT_EXEC = os.getenv("AIFAMILY_AGENT_EXEC")  # 在 agent-core 容器内执行命令的入口
PROVIDERS = ["deepseek", "kimi", "claude"]  # 三后端模型别名（网关 dispatch）
GENEROUS_BUDGET = 5.0  # 创建时给足额度，预算用例再据真实成本收紧（确定性）


def _in_agent_container(cmd: list[str]):
    import subprocess

    if not AGENT_EXEC:
        pytest.skip("设 AIFAMILY_AGENT_EXEC（如 'docker compose exec -T agent-core'）")
    return subprocess.run(AGENT_EXEC.split() + cmd, capture_output=True, text=True, timeout=30)


@pytest.fixture
def vkeys():
    """以 master key 在隔离租户创建两个虚拟 key（function-scoped，每用例独立）；用后删除清理。"""
    litellm = require("litellm")
    master = os.environ["AIFAMILY_LITELLM_MASTER_KEY"]
    hdr = {"Authorization": f"Bearer {master}"}
    created = {}
    for member in ("A", "B"):
        r = httpx.post(
            f"{litellm}/key/generate",
            headers=hdr,
            json={"max_budget": GENEROUS_BUDGET, "models": PROVIDERS, "metadata": {"member": member}},
            timeout=30,
        )
        r.raise_for_status()
        created[member] = r.json()["key"]
    yield litellm, master, created
    for key in created.values():
        httpx.post(f"{litellm}/key/delete", headers=hdr, json={"keys": [key]}, timeout=30)


def _key_spend(litellm, master, key) -> float:
    r = httpx.get(
        f"{litellm}/key/info", headers={"Authorization": f"Bearer {master}"},
        params={"key": key}, timeout=30,
    )
    r.raise_for_status()
    info = r.json().get("info", r.json())
    return float(info["spend"])


def _set_budget(litellm, master, key, max_budget):
    httpx.post(
        f"{litellm}/key/update", headers={"Authorization": f"Bearer {master}"},
        json={"key": key, "max_budget": max_budget}, timeout=30,
    ).raise_for_status()


def _chat(litellm, key, model, content="hi"):
    return httpx.post(
        f"{litellm}/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role": "user", "content": content}]},
        timeout=60,
    )


def test_agent_core_cannot_egress_to_providers():
    for host in ("api.deepseek.com", "api.moonshot.cn", "api.anthropic.com"):
        res = _in_agent_container(
            ["python", "-c", f"import socket; socket.create_connection(('{host}',443),3)"]
        )
        assert res.returncode != 0, f"agent-core 不得直连厂商：{host}"


def test_agent_core_can_reach_litellm():
    res = _in_agent_container(
        ["python", "-c", "import socket; socket.create_connection(('litellm',4000),3)"]
    )
    assert res.returncode == 0, "agent-core 应可达 litellm:4000"


def test_llm_client_fail_closed_when_gateway_down():
    """LiteLLM 不可达时 Agent 明确失败/安全降级，无厂商直连。"""
    agent = require("base_url")
    r = httpx.post(f"{agent}/internal/test/llm_with_gateway_down", timeout=30)
    assert r.status_code in (503, 424)
    assert r.json()["provider_direct_call"] is False


@pytest.mark.parametrize("model", PROVIDERS)
def test_three_providers_real_completion(vkeys, model):
    litellm, _master, keys = vkeys
    r = _chat(litellm, keys["A"], model)
    assert r.status_code == 200, f"{model} 真实 completion 应成功（路由到对应后端）"
    assert r.json()["choices"][0]["message"]["content"]


def test_per_user_budget_blocks_over_limit_and_is_independent(vkeys):
    litellm, master, keys = vkeys
    # 校准：A 发一次真实 completion，读其实际已计成本（与模型成本无关，确定性）
    assert _chat(litellm, keys["A"], "deepseek").status_code == 200
    spend = _key_spend(litellm, master, keys["A"])
    assert spend > 0, "校准调用未产生可计量成本，无法确定性验预算"
    # 把 A 预算收紧到低于已计成本 → 已超额 → 下一次调用必被阻断
    _set_budget(litellm, master, keys["A"], spend / 2)
    over = _chat(litellm, keys["A"], "deepseek")
    assert over.status_code == 429, "A 超预算后须被网关 429/阻断（确定性）"
    # B 计量独立，预算充足 → 成功
    assert _chat(litellm, keys["B"], "deepseek").status_code == 200, "B 计量须与 A 相互独立"


@pytest.mark.parametrize("bad_key", ["", "wrong-key"])
def test_missing_or_wrong_vkey_rejected(bad_key):
    litellm = require("litellm")
    assert _chat(litellm, bad_key, "deepseek").status_code in (401, 403)
