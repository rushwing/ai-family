"""Version-1 HTTP projections. Canonical validation remains in shared contracts."""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, JsonValue
from state_schema.home_inventory import AreaType, ResidenceType

T = TypeVar("T")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Home(Model):
    id: str
    name: str
    residence_type: ResidenceType


class Area(Model):
    id: str
    home_id: str
    area_type: AreaType
    name: str
    floor_id: str | None
    labels: list[str]
    aliases: list[str]


class Device(Model):
    id: str
    home_id: str
    name: str
    area_id: str | None
    labels: list[str]


class Ordering(Model):
    epoch: int
    sequence: int


class Observation(Model):
    status: Literal["known", "unknown"]
    value: str | int | float | bool | None
    observed_at: str | None
    ordering: Ordering | None


class Availability(Model):
    status: Literal["online", "offline", "unknown"]
    observed_at: str | None
    ordering: Ordering | None


class DesiredState(Model):
    revision: int
    values: dict[str, str | int | float | bool | None]
    report_baseline: Ordering | None


class State(Model):
    home_id: str
    device_id: str
    desired_state: DesiredState | None
    reported_state: dict[str, Observation]
    availability: Availability


class StateView(Model):
    status: Literal["found"]
    state: State
    revision: int
    updated_at_ms: int | None
    freshness: Literal["uninitialized", "fresh", "stale"]


class Descriptor(Model):
    schema_version: Literal[1]
    capability_id: str
    capability_version: int
    title: str
    description: str
    properties: dict[str, JsonValue]
    actions: dict[str, JsonValue]
    events: dict[str, JsonValue]


class Capabilities(Model):
    status: Literal["found", "uninitialized"]
    data: list[Descriptor] | None


class Snapshot(Model):
    home: Home
    areas: list[Area]
    devices: list[Device]
    states: list[StateView]


class DeviceDetail(Model):
    device: Device
    state: StateView
    capabilities: Capabilities


class Found(Model, Generic[T]):
    status: Literal["found"] = "found"
    data: T


class Missing(Model):
    status: Literal["not_found"] = "not_found"
    data: None = None


class ErrorCode(Model):
    code: Literal[
        "unauthenticated",
        "forbidden",
        "invalid_request",
        "state_unavailable",
        "internal_error",
        "not_found",
        "method_not_allowed",
    ]


class Error(Model):
    error: ErrorCode
