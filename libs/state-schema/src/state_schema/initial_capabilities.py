"""REQ-017 initial vocabulary; reading the fixed resource never executes actions.

Consumers interpret units/direction by an explicitly supported identity/revision,
not by parsing descriptions. Importing this module does not read the catalogue.
"""

from importlib.resources import files

from .capability import CapabilityCatalogue, CapabilityError, load_capabilities_json

_IDENTITIES = (
    "home.switchable",
    "home.positionable",
    "home.temperature_sensor",
    "home.humidity_sensor",
    "home.power_meter",
    "home.battery_powered",
)


def load_initial_capabilities() -> CapabilityCatalogue:
    """Read and validate a fresh revision-1 catalogue from the package resource.

    No cache, caller path, environment lookup or provider operation is involved.
    Missing/unreadable resources fail closed without exposing paths or contents.
    """
    try:
        text = (
            files("state_schema")
            .joinpath("initial_capabilities.v1.json")
            .read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError):
        raise CapabilityError(
            ("capabilities",), "initial catalogue resource is unreadable"
        ) from None
    catalogue = load_capabilities_json(text)
    if tuple(
        (item.capability_id, item.capability_version) for item in catalogue.capabilities
    ) != tuple((identity, 1) for identity in _IDENTITIES):
        raise CapabilityError(("capabilities",), "initial catalogue identities or revisions differ")
    return catalogue
