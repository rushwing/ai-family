"""Allow gateway and goal_mcp packages to be tested in-place."""

import sys
from pathlib import Path

_GATEWAY_ROOT = Path(__file__).resolve().parents[1]
_GOAL_MCP_ROOT = _GATEWAY_ROOT.parent / "goal-mcp"

for path in (_GATEWAY_ROOT, _GOAL_MCP_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
