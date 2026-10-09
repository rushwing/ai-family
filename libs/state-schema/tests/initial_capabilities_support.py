"""REQ-017 approved vocabulary and real accessor test boundary."""

from importlib.util import find_spec

import pytest

initial_required = pytest.mark.skipif(
    find_spec("state_schema.initial_capabilities") is None,
    reason="REQ-017 initial Capability runtime absent; acceptance pending",
)

# Independent expected contracts transcribed from the reviewed REQ table.
CONTRACTS = [
    ("home.switchable", "Switchable", "is_on", {"type": "boolean"}, False),
    (
        "home.positionable",
        "Positionable",
        "position_percent",
        {"type": "integer", "minimum": 0, "maximum": 100},
        False,
    ),
    (
        "home.temperature_sensor",
        "TemperatureSensor",
        "temperature_c",
        {"type": "number", "minimum": -273.15},
        True,
    ),
    (
        "home.humidity_sensor",
        "HumiditySensor",
        "relative_humidity_percent",
        {"type": "number", "minimum": 0, "maximum": 100},
        True,
    ),
    ("home.power_meter", "PowerMeter", "power_w", {"type": "number"}, True),
    (
        "home.battery_powered",
        "BatteryPowered",
        "battery_percent",
        {"type": "number", "minimum": 0, "maximum": 100},
        True,
    ),
]
ACTIONS = [
    ("home.switchable", "set_on", "is_on", {"type": "boolean"}, 30000, False),
    (
        "home.positionable",
        "set_position",
        "position_percent",
        {"type": "integer", "minimum": 0, "maximum": 100},
        120000,
        50,
    ),
]
RESOURCE = "initial_capabilities.v1.json"


def inject_resource(monkeypatch, initial_api, text=None, error=None):
    """Replace only the resource read; actual loader/validators still execute."""
    calls = []

    class Resource:
        def joinpath(self, name):
            calls.append(("joinpath", name))
            return self

        def read_text(self, encoding):
            calls.append(("read_text", encoding))
            if error is not None:
                raise error
            return text

    def files(package):
        calls.append(("files", package))
        return Resource()

    monkeypatch.setattr(initial_api, "files", files)
    return calls
