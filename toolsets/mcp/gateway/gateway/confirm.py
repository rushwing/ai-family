"""两段式写操作 confirm token —— REQ-003 WP-4 / TC-003-04（B）。

confirm token 的红线（与 WP-7 kid Draft-First 同源理念）：
  - **用户来源**：只能由 /tools/{write} 的 prepare 阶段签发（代表 ChatUI 用户点击），
    Agent/Planner 不能自我生成；网关只认自己签发并记账的 token。
  - **成员 + 工具绑定**：token 绑定签发时的 family_member_id 与 tool，跨成员/换工具复用一律拒。
  - **一次性**：消费即作废（consumed），重放拒。

M1 用进程内存储（网关单实例）；多实例 / 持久化随平台状态表（confirm_token 表，已在
data/migrations/0005）在后续切片接 PG。
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass


@dataclass
class _Entry:
    member: str
    tool: str
    issued_at: float
    consumed: bool = False


class ConfirmStore:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._tokens: dict[str, _Entry] = {}

    def issue(self, *, member: str, tool: str) -> str:
        token = "cf_" + secrets.token_urlsafe(24)
        with self._lock:
            self._tokens[token] = _Entry(member=member, tool=tool, issued_at=time.time())
        return token

    def consume(self, token: str | None, *, member: str, tool: str) -> bool:
        """原子校验+消费。仅当 token 由网关签发、未过期、未消费、且 member+tool 匹配时成功。

        任一不符（缺失 / 伪造 / Agent 自生成 / 过期 / 已用 / 跨成员 / 换工具）→ False。
        """
        if not token:
            return False
        with self._lock:
            entry = self._tokens.get(token)
            if entry is None:  # 伪造 / Agent 自生成 —— 网关从未签发
                return False
            if entry.consumed:
                return False
            if time.time() - entry.issued_at > self._ttl:
                return False
            if entry.member != member or entry.tool != tool:
                return False
            entry.consumed = True
            return True
