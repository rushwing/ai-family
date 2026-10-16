"""Installed lifecycle checks with explicit assertions that survive python -O."""

import asyncio
import hashlib
import importlib.metadata
import json
from pathlib import Path

import certifi
from home_device_fabric.ha_configuration import HAConfiguration
from home_device_fabric.ha_websocket import HAWebSocketClient, _tls_context
from websockets.asyncio.server import serve

TOKEN = "fictional-installed-websocket-token"


def require(condition):
    if not condition:
        raise RuntimeError("installed_websocket_check_failed")


async def wait_state(client, state):
    async with asyncio.timeout(5):
        while client.health().state != state:
            await asyncio.sleep(0)


async def main():
    # Inspect the actual client context, not just certifi's bundle on disk.
    trusted_roots = len(_tls_context().get_ca_certs())
    require(trusted_roots > 0)
    auth = []
    mode = "connected"

    async def handler(ws):
        require(ws.request.path == "/api/websocket")
        await ws.send('{"type":"auth_required"}')
        auth.append(json.loads(await ws.recv()))
        require(auth[-1] == {"type": "auth", "access_token": TOKEN})
        if mode == "auth_failed":
            await ws.send('{"type":"auth_invalid","message":"' + TOKEN + '"}')
            return
        await ws.send('{"type":"auth_ok"}')
        if mode == "disconnect":
            await ws.close()
        else:
            await ws.wait_closed()

    async with serve(handler, "127.0.0.1", 0, compression=None) as server:
        port = server.sockets[0].getsockname()[1]

        def client():
            return HAWebSocketClient(HAConfiguration(
                {"schema_version": 1, "base_url": f"http://127.0.0.1:{port}",
                 "reconnect_initial_delay_ms": 1, "reconnect_max_attempts": 1},
                access_token=TOKEN))

        connected = client()
        running = asyncio.create_task(connected.run())
        await wait_state(connected, "connected")
        require(not running.done())
        require(connected.health().reconnect_attempt == 0)
        await asyncio.gather(connected.aclose(), connected.aclose())
        await running
        require(connected.health().state == "closed")

        mode = "auth_failed"
        rejected = client()
        await asyncio.wait_for(rejected.run(), 5)
        require(rejected.health().state == "auth_failed")
        require(rejected.health().reconnect_attempt == 0)
        require(TOKEN not in repr(rejected) + repr(rejected.health()))
        await rejected.aclose()
        require(rejected.health().state == "closed")
        require(rejected.health().reason == "auth_failed")

        mode = "disconnect"
        disconnected = client()
        await asyncio.wait_for(disconnected.run(), 5)
        require(disconnected.health().state == "failed")
        require(disconnected.health().reason == "reconnect_exhausted")
        require(disconnected.health().reconnect_attempt == 1)
        require(len(auth) == 4)
        await disconnected.aclose()
        require(disconnected.health().state == "closed")
        require(disconnected.health().reason == "reconnect_exhausted")
        await disconnected.aclose()

    print(json.dumps({"profile": "req024-installed-lifecycle-v1", "wire_auths": len(auth),
                      "checks": ["authenticated", "shutdown", "auth_rejected", "finite_retry",
                                 "loaded_trust_roots"],
                      "loaded_ca_count": trusted_roots,
                      "websockets": importlib.metadata.version("websockets"),
                      "certifi": importlib.metadata.version("certifi"),
                      "ca_bundle_sha256": hashlib.sha256(
                          Path(certifi.where()).read_bytes()).hexdigest()}))


if __name__ == "__main__":
    asyncio.run(main())
