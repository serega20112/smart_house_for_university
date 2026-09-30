"""Domain enumerations."""

from smart_home_backend.domain.enums.base import StrEnum
from smart_home_backend.domain.enums.device import (
    RELAY_CHANNEL_COUNT,
    Capability,
    ControlSource,
    DeviceStatus,
    DeviceType,
    RelayState,
    parse_capability,
    parse_device_type,
)
from smart_home_backend.domain.enums.intent import ACTION_INTENTS, READ_INTENTS, Intent
from smart_home_backend.domain.enums.operation import ClarificationReason, OperationStatus
from smart_home_backend.domain.enums.scenario import CompletionBehavior, ScenarioStatus

__all__ = [
    "ACTION_INTENTS",
    "READ_INTENTS",
    "RELAY_CHANNEL_COUNT",
    "Capability",
    "ClarificationReason",
    "CompletionBehavior",
    "ControlSource",
    "DeviceStatus",
    "DeviceType",
    "Intent",
    "OperationStatus",
    "RelayState",
    "ScenarioStatus",
    "StrEnum",
    "parse_capability",
    "parse_device_type",
]
