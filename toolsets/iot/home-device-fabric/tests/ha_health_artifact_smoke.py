"""Installed composition checks; explicit require remains effective under -O."""

import asyncio
import json
import logging

from home_device_fabric.ha_configuration import HAConfiguration
from home_device_fabric.ha_health import HAHealthMonitor
from websockets.asyncio.server import serve

TOKEN = "fictional-installed-health-token"


def require(condition):
    if not condition:
        raise RuntimeError("installed_health_check_failed")


async def wait_for(predicate):
    async with asyncio.timeout(5):
        while not predicate():
            await asyncio.sleep(.001)


async def check():
    mode = {"rest": 200, "socket": "ok"}
    auth, requests, sockets = [], [], []
    logger = logging.Logger("fictional-health-peer")
    logger.disabled = True

    async def process(connection, request):
        if request.path != "/api/config":
            return None
        require(request.headers["Authorization"] == "Bearer " + TOKEN)
        requests.append(request.path)
        response = connection.respond(mode["rest"], json.dumps(
            {"version": "fixture-health", "ignored": TOKEN}))
        del response.headers["Content-Type"]
        response.headers["Content-Type"] = "application/json"
        return response

    async def handler(ws):
        require(ws.request.path == "/api/websocket")
        await ws.send('{"type":"auth_required"}')
        received = json.loads(await ws.recv())
        require(received == {"type": "auth", "access_token": TOKEN})
        auth.append(True)
        if mode["socket"] == "reject":
            await ws.send(json.dumps({"type": "auth_invalid", "message": TOKEN}))
            return
        sockets.append(ws)
        await ws.send('{"type":"auth_ok"}')
        await ws.wait_closed()

    async with serve(handler, "127.0.0.1", 0, compression=None,
                     process_request=process, logger=logger) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        config = HAConfiguration({"schema_version": 1, "base_url": url,
                                  "request_timeout_ms": 1000,
                                  "reconnect_initial_delay_ms": 10,
                                  "reconnect_max_attempts": 1}, access_token=TOKEN)
        client = HAHealthMonitor(config, observation_interval_ms=50)
        running = asyncio.create_task(client.run())
        try:
            await wait_for(lambda: client.health().state == "connected")
            mode["rest"] = 401
            await wait_for(lambda: client.health().rest_state == "auth_failed")
            require(client.health().state == "auth_failed")
            require(client.health().event_stream_connected)
            mode["rest"] = 200
            await wait_for(lambda: client.health().state == "connected")
            await sockets[-1].close()
            await wait_for(lambda: client.health().websocket.reconnect_attempt == 1
                           and client.health().state == "connected")
            require(len(auth) == 2)
            await sockets[-1].close()
            await wait_for(lambda: client.health().websocket.state == "failed")
            require(client.health().state == "disconnected")
            require(client.health().websocket.reason == "reconnect_exhausted")
            require(not running.done())  # Terminal socket never restarts, REST still monitored.
            diagnostics = repr(client) + json.dumps(client.health().to_dict())
            require(TOKEN not in diagnostics and url not in diagnostics)
            require("fixture-health" not in diagnostics)
        finally:
            await client.aclose()
            await running
        frozen = client.health()
        await client.aclose()
        require(client.health() is frozen)
        require(frozen.state == "closed" and frozen.rest_reachable is None)
        require(not frozen.event_stream_connected)

        mode["socket"] = "reject"
        rejected = HAHealthMonitor(config, observation_interval_ms=50)
        rejecting = asyncio.create_task(rejected.run())
        try:
            await wait_for(lambda: rejected.health().websocket.state == "auth_failed")
            require(rejected.health().state == "auth_failed")
            require(rejected.health().websocket.reconnect_attempt == 0)
            require(len(auth) == 3)
            require(TOKEN not in repr(rejected.health()))
        finally:
            await rejected.aclose()
            await rejecting
        require(not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()
                     and task.get_name().startswith("ha-health-")])
    return {"profile": "req026-installed-health-v1", "wire_auths": len(auth),
            "rest_requests": len(requests),
            "checks": ["connected", "independent_rest_auth", "rest_recovery",
                       "finite_socket_reconnect", "terminal_socket_not_restarted",
                       "socket_auth_rejected", "redaction", "closed_snapshot", "drained"]}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(check())))
