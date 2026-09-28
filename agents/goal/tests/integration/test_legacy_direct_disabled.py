"""REQ-003 WP-4: old REST/FastMCP endpoints are not public entry points."""

import pytest

from app.main import settings


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/v1/tracks/categories", "/mcp"])
async def test_legacy_direct_paths_return_410(client, path):
    original = settings.GATEWAY_INTERNAL_TOKEN
    settings.GATEWAY_INTERNAL_TOKEN = ""
    try:
        response = await client.get(path)
    finally:
        settings.GATEWAY_INTERNAL_TOKEN = original
    assert response.status_code == 410


@pytest.mark.asyncio
async def test_only_configured_gateway_token_can_reach_internal_routes(client):
    original = settings.GATEWAY_INTERNAL_TOKEN
    settings.GATEWAY_INTERNAL_TOKEN = "internal-test-token"
    try:
        denied = await client.get("/api/v1/not-a-route")
        forwarded = await client.get(
            "/api/v1/not-a-route",
            headers={"X-AI-Family-Gateway-Token": "internal-test-token"},
        )
    finally:
        settings.GATEWAY_INTERNAL_TOKEN = original
    assert denied.status_code == 410
    assert forwarded.status_code == 404
