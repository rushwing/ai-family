"""ai-family MCP 网关（信任边界）—— REQ-003 WP-4。

入口：gateway.app:app（FastAPI）。运行：
    uvicorn gateway.app:app --port 8080
环境变量：AIFAMILY_OIDC_ISSUER / AIFAMILY_OIDC_AUD。
"""
from gateway.app import create_app

__all__ = ["create_app"]
