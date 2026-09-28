"""让 `import goal_mcp` 在未安装包时也可解析（就地跑 tests/ 用）。

REQ-005 接 uv workspace + CI 后由 workspace pythonpath 统一；此前本地以此 conftest 兜底。
"""
import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))
