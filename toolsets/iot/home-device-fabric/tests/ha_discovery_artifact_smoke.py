"""Real installed read-only discovery; explicit checks survive optimized Python."""

import asyncio
import json
import logging

TOKEN = "fictional-discovery-credential"
COMPONENTS = ("devices", "entities", "areas", "states")
COMMANDS = (
    "config/device_registry/list",
    "config/entity_registry/list",
    "config/area_registry/list",
    "get_states",
)


def fixture():
    return {
        "devices": [{"id": "provider-device", "area_id": "provider-area", "name": TOKEN}],
        "entities": [
            {
                "entity_id": "switch.fixture",
                "device_id": "provider-device",
                "area_id": None,
                "disabled_by": None,
            }
        ],
        "areas": [{"area_id": "provider-area", "name": "Fictional"}],
        "states": [
            {
                "entity_id": "switch.fixture",
                "state": "off",
                "attributes": {"value": 0, "enabled": False, "private": TOKEN},
            }
        ],
    }


async def check():
    async with asyncio.timeout(15):
        return await _check()


async def _check():
    from home_device_fabric.ha_configuration import HAConfiguration
    from home_device_fabric.ha_discovery import HADiscoveryError, HARegistryDiscoveryClient
    from websockets.asyncio.server import serve

    checks = 0

    def require(value):
        nonlocal checks
        checks += 1
        if not value:
            raise RuntimeError("installed_discovery_check_failed")

    state = {"mode": "success", "connections": 0, "commands": [], "active": 0}
    errors = []
    logger = logging.Logger("fictional-discovery-peer")
    logger.disabled = True

    async def handler(ws):
        state["connections"] += 1
        state["active"] += 1
        try:
            if ws.request.path != "/api/websocket":
                raise RuntimeError("wrong_path")
            await ws.send('{"type":"auth_required","ha_version":"fixture"}')
            if json.loads(await ws.recv()) != {"type": "auth", "access_token": TOKEN}:
                raise RuntimeError("wrong_auth")
            await ws.send('{"type":"auth_ok","ha_version":"fixture"}')
            for identifier, (component, command) in enumerate(zip(COMPONENTS, COMMANDS), 1):
                received = json.loads(await ws.recv())
                if received != {"id": identifier, "type": command}:
                    raise RuntimeError("wrong_command")
                state["commands"].append(received)
                if state["mode"] == "denied" and component == "entities":
                    await ws.send(
                        json.dumps(
                            {
                                "id": identifier,
                                "type": "result",
                                "success": False,
                                "error": {"code": "unauthorized", "message": TOKEN},
                            }
                        )
                    )
                    await ws.wait_closed()
                    return
                rows = [] if state["mode"] == "empty" else fixture()[component]
                await ws.send(
                    json.dumps(
                        {"id": identifier, "type": "result", "success": True, "result": rows}
                    )
                )
            await ws.wait_closed()
        except Exception:
            errors.append("peer_failed")
        finally:
            state["active"] -= 1

    async with serve(handler, "127.0.0.1", 0, compression=None, logger=logger) as server:
        port = server.sockets[0].getsockname()[1]
        config = HAConfiguration(
            {
                "schema_version": 1,
                "base_url": f"http://127.0.0.1:{port}",
                "request_timeout_ms": 2000,
            },
            access_token=TOKEN,
        )
        async with HARegistryDiscoveryClient(config) as client:
            first = await client.discover()
            require(first.for_mapping() == fixture())
            require(
                first.to_redacted_dict()
                == {"complete": True, "counts": dict.fromkeys(COMPONENTS, 1)}
            )
            detached = first.for_mapping()
            detached["states"][0]["attributes"].clear()
            require(first.for_mapping()["states"] == fixture()["states"])
            require(TOKEN not in repr(first) + repr(client) + repr(first.to_redacted_dict()))
            require((await client.discover()).for_mapping() == fixture())
            require(state["connections"] == 2 and len(state["commands"]) == 8)
            state["mode"] = "denied"
            try:
                await client.discover()
            except HADiscoveryError as error:
                require(
                    error.to_dict()
                    == {"code": "permission_denied", "stage": "entities", "completed": ["devices"]}
                )
                require(error.__context__ is None and error.__cause__ is None)
                require(TOKEN not in str(error) + repr(error) + repr(error.to_dict()))
            else:
                require(False)
            require(len(state["commands"]) == 10)
            state["mode"] = "empty"
            empty = await client.discover()
            require(empty.for_mapping() == dict(zip(COMPONENTS, ([], [], [], []))))
            require(empty.to_redacted_dict()["counts"] == dict.fromkeys(COMPONENTS, 0))
            require(first.for_mapping() == fixture())
        try:
            await client.discover()
        except HADiscoveryError as error:
            require(error.code == "client_closed")
        else:
            require(False)
    require(not errors and state["active"] == 0 and state["connections"] == 4)
    return {"checks": checks, "loopback": True, "device_writes": 0}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(check()), sort_keys=True))
