# libs/ —— 共享契约（跨模块唯一来源）

跨层共享的东西**一律进 `libs/`，且只进 `libs/`**；Agent 之间禁止横向 import 彼此 `src/`，
只依赖 `libs/` 契约——让"同仓"不等于"耦合成一坨"，也让未来 `git subtree split` 依赖可断
（ADR-013 / [07 §5](../docs/design/07-repo-strategy.html)）。

分层子包（REQ-006，**禁 `libs/common` 万能包**，不得反向依赖业务）：

| 子包 | 职责 |
|---|---|
| `agent-sdk/` | LangGraph 基类 / ReAct 骨架 |
| `mcp-contracts/` | 工具调用信封 / schema |
| `state-schema/` | checkpointer 状态模型 |
| `auth/` | JWT/OIDC 校验 · RLS 会话变量 |

依赖方向硬约束：`agents/* · toolsets/* · apps/*` → `libs/*`，反向禁止。bootstrap 期由 `tools/check_layout.py`
做轻量横向 import 护栏；完整 import-linter 配置与阻塞门随 REQ-006 落地。各子包内部 Python 包（underscore 命名）
与 `pyproject` 亦随首次实现填充。
