"""Real loopback subscription checks for isolated direct and sdist wheel pairs."""

import asyncio
import json
import logging
import pickle

from home_device_fabric.ha_configuration import HAConfiguration
from home_device_fabric.ha_subscription import HAStateSubscriptionClient
from websockets.asyncio.server import serve

TOKEN = "fictional-installed-subscription-token"


def require(condition):
    if not condition:
        raise RuntimeError("installed_subscription_check_failed")


async def wait_for(predicate):
    async with asyncio.timeout(5):
        while not predicate():
            await asyncio.sleep(.001)


async def check():
    state = {"connections": 0, "active": 0, "commands": 0}
    errors, delivered = [], []
    admission, release = asyncio.Event(), asyncio.Event()
    logger = logging.Logger("fictional-subscription-peer")
    logger.disabled = True

    async def handler(ws):
        state["connections"] += 1
        ordinal = state["connections"]
        state["active"] += 1
        try:
            require(ws.request.path == "/api/websocket")
            await ws.send('{"type":"auth_required"}')
            require(json.loads(await ws.recv()) == {"type": "auth", "access_token": TOKEN})
            await ws.send('{"type":"auth_ok"}')
            require(json.loads(await ws.recv()) == {
                "id": 1, "type": "subscribe_events", "event_type": "state_changed"})
            state["commands"] += 1
            if ordinal == 1:
                admission.set()
                await release.wait()
            if ordinal == 3:
                await ws.send(json.dumps({"id": 1, "type": "result", "success": False,
                                          "error": {"code": "not_allowed", "message": TOKEN}}))
                await ws.wait_closed()
                return
            await ws.send('{"id":1,"type":"result","success":true,"result":null}')
            await ws.send(json.dumps({"id": 1, "type": "event", "event": {
                "event_type": "state_changed", "data": {
                    "entity_id": "sensor.fixture", "old_state": None,
                    "new_state": {"state": str(ordinal)}}}}))
            if ordinal == 1:
                await ws.close()
            else:
                await ws.wait_closed()
        except Exception:
            errors.append("peer_failed")
        finally:
            state["active"] -= 1

    async def callback(event):
        require(event["event_type"] == "state_changed")
        require(event["data"]["entity_id"] == "sensor.fixture")
        delivered.append(event["data"]["new_state"]["state"])

    async with serve(handler, "127.0.0.1", 0, compression=None, logger=logger) as server:
        port = server.sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        config = HAConfiguration({"schema_version": 1, "base_url": url,
                                  "request_timeout_ms": 1000,
                                  "reconnect_initial_delay_ms": 10,
                                  "reconnect_max_attempts": 1}, access_token=TOKEN)
        client = HAStateSubscriptionClient(config, callback)
        require(client.subscription_health().state == "idle")
        running = asyncio.create_task(client.run())
        try:
            async with asyncio.timeout(5):
                await admission.wait()
            require(client.health().state == "connected")
            require(not client.subscription_health().subscribed)
            release.set()
            await wait_for(lambda: len(delivered) == 2)
            require(client.subscription_health().subscribed)
            require(client.health().reconnect_attempt == 1)
            require(delivered == ["1", "2"] and state["commands"] == 2)
            diagnostics = repr(client) + json.dumps(client.subscription_health().to_dict())
            require(TOKEN not in diagnostics and url not in diagnostics)
            for operation in (pickle.dumps,):
                try:
                    operation(client)
                except TypeError as error:
                    require(str(error) == "client_serialization_refused")
                else:
                    require(False)
        finally:
            await client.aclose()
            await running
        await wait_for(lambda: state["active"] == 0)
        frozen = client.subscription_health()
        await client.aclose()
        require(client.subscription_health() is frozen and frozen.state == "closed")
        require(not frozen.subscribed)
        rejected = HAStateSubscriptionClient(config, callback)
        await rejected.run()
        require(rejected.subscription_health().state == "rejected")
        require(rejected.subscription_health().reason == "subscription_rejected")
        require(not rejected.subscription_health().subscribed)
        require(TOKEN not in repr(rejected.subscription_health()))
        await rejected.aclose()
        await wait_for(lambda: state["active"] == 0)
        require(not errors and state["connections"] == state["commands"] == 3)
        require(not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()
                     and t.get_name().startswith("ha-websocket-")])
    return {"profile": "req027-installed-subscription-v1", "connections": state["connections"],
            "delivered": len(delivered), "active_after_close": state["active"],
            "checks": ["ack_readiness", "ordered_events", "one_subscription_per_socket",
                       "reconnect", "rejection", "redaction", "serialization", "drained"]}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(check())))
