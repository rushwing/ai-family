"""TC-003-05：GoalAgent 归档存储（MinIO+PG 版本表）与统一通知出口（notify.out）。

需求 5。

env-gated：未设 AIFAMILY_MINIO_URL / AIFAMILY_AMQP_URL 或外部通道改造（WP-5）
尚未落地时 skip；req_impl 起 MinIO + broker 后转 passing。
"""
import os

import pytest

MINIO = os.getenv("AIFAMILY_MINIO_URL")
AMQP = os.getenv("AIFAMILY_AMQP_URL")
pytestmark = pytest.mark.skipif(
    not (MINIO and AMQP), reason="设 AIFAMILY_MINIO_URL + AIFAMILY_AMQP_URL 运行归档/通知用例"
)

archive = pytest.importorskip("app.services.archive_service", reason="MinIO 归档未落地（WP-5）")
notify = pytest.importorskip("app.channels.notify", reason="notify.out 出口未落地（WP-5）")


def test_report_archived_to_minio_with_pg_version():
    ref = archive.archive_report(member="A", content=b"weekly-v1")
    assert archive.read_object(ref) == b"weekly-v1"
    v2 = archive.archive_report(member="A", report_id=ref.report_id, content=b"weekly-v2")
    versions = archive.list_versions(ref.report_id)
    assert [v.version for v in versions] == [1, 2]
    assert v2.previous_version == 1  # PG 版本表保存可追溯关系


def test_m1_does_not_call_github_or_telegram_direct(monkeypatch):
    calls = []
    monkeypatch.setattr(archive, "_github_client", lambda *a, **k: calls.append("github"))
    monkeypatch.setattr(notify, "_telegram_client", lambda *a, **k: calls.append("telegram"))
    archive.archive_report(member="A", content=b"x")
    notify.send(member="A", template="checkin_ack", idempotency_key="k1")
    assert calls == [], "M1 不得直连 GitHub 归档或 Telegram"


def test_notify_only_via_notify_out_and_idempotent():
    consumer = notify.test_consumer()
    notify.send(member="A", template="reminder", idempotency_key="k-dup")
    notify.send(member="A", template="reminder", idempotency_key="k-dup")  # 重复投递
    msgs = consumer.drain(topic="notify.out")
    assert len(msgs) == 1, "重复 idempotency_key 不得重复投递"
    assert msgs[0]["family_member_id"] == "A"
