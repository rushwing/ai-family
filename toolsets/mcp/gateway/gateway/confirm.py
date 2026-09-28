"""两段式写操作 confirm token —— REQ-003 WP-4 / TC-003-04（B）。

confirm token 的红线（与 WP-7 kid Draft-First 同源理念）：
  - **用户来源**：只能由持有独立 HMAC 密钥的 ChatUI/BFF 交互通道证明用户点击后签发，
    普通 Agent bearer 不能自我生成或请求签发。
  - **会话 + 成员 + 工具 + payload 绑定**：token 绑定 OIDC session、family_member_id、
    tool 与规范化业务参数；跨会话、跨成员、换工具或确认后替换参数一律拒。
  - **一次性**：消费即作废（consumed），重放拒。

M1 边界测试使用有 TTL 和容量上限的进程内存储；多实例 / 持久化随平台状态表
（confirm_token 表，已在 data/migrations/0005）在后续联调接 PG。
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    member: str
    session: str
    tool: str
    payload_digest: str
    issued_at: float


def confirmation_payload(params: dict[str, Any]) -> dict[str, Any]:
    """Return the exact business payload covered by user confirmation.

    Transport-only fields differ between confirmation and execute and therefore
    are excluded.  Every other field, including ``family_member_id`` and
    ``idempotency_key``, is part of the confirmation contract.
    """
    return {
        key: value
        for key, value in params.items()
        if key not in {"prepare", "confirm_token"}
    }


def payload_digest(params: dict[str, Any]) -> str:
    canonical = json.dumps(
        confirmation_payload(params),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class ConfirmStore:
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 10_000) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._tokens: dict[str, _Entry] = {}

    def _purge_expired_locked(self, now: float) -> None:
        expired = [
            token
            for token, entry in self._tokens.items()
            if now - entry.issued_at > self._ttl
        ]
        for token in expired:
            self._tokens.pop(token, None)

    def issue(
        self, *, member: str, session: str, tool: str, params: dict[str, Any]
    ) -> str:
        token = "cf_" + secrets.token_urlsafe(24)
        now = time.time()
        with self._lock:
            self._purge_expired_locked(now)
            while len(self._tokens) >= self._max_entries:
                self._tokens.pop(next(iter(self._tokens)))
            self._tokens[token] = _Entry(
                member=member,
                session=session,
                tool=tool,
                payload_digest=payload_digest(params),
                issued_at=now,
            )
        return token

    def consume(
        self,
        token: str | None,
        *,
        member: str,
        session: str,
        tool: str,
        params: dict[str, Any],
    ) -> bool:
        """Atomically validate and consume a payload-bound confirmation.

        Missing, forged, expired, replayed, cross-session, cross-member,
        cross-tool, or payload-mutated confirmations all fail closed.
        """
        if not token:
            return False
        now = time.time()
        with self._lock:
            self._purge_expired_locked(now)
            entry = self._tokens.get(token)
            if entry is None:  # 伪造 / Agent 自生成 —— 网关从未签发
                return False
            if entry.member != member or entry.session != session or entry.tool != tool:
                return False
            if entry.payload_digest != payload_digest(params):
                return False
            # Removal both bounds memory and preserves replay rejection: a
            # repeated token is indistinguishable from an unsigned token.
            self._tokens.pop(token, None)
            return True

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired_locked(time.time())
            return len(self._tokens)
