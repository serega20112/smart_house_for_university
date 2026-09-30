"""Domain layer facade.

Re-exports the business vocabulary so that other layers can import the domain
through a single stable module. The domain depends on no outer layer.
"""

from smart_home_backend.domain.entities import (
    AutomationSettings,
    ClimateReading,
    Device,
    HomeState,
    Relay,
    Scenario,
    ScenarioAction,
    Sensor,
)
from smart_home_backend.domain.enums import (
    ACTION_INTENTS,
    READ_INTENTS,
    RELAY_CHANNEL_COUNT,
    Capability,
    ClarificationReason,
    CompletionBehavior,
    ControlSource,
    DeviceStatus,
    DeviceType,
    Intent,
    OperationStatus,
    RelayState,
    ScenarioStatus,
    parse_capability,
    parse_device_type,
)
from smart_home_backend.domain.exceptions import (
    ChannelConflictError,
    DeviceNotFoundError,
    DomainError,
    InvalidClimateValueError,
    UnsupportedCapabilityError,
)
from smart_home_backend.domain.policies import (
    ClimateDemand,
    evaluate,
    evaluate_humidity,
    evaluate_temperature,
    find_all_for_capability,
    find_device_by_name,
    find_device_for_capability,
    has_timed_out,
    is_goal_reached,
)
from smart_home_backend.domain.value_objects.climate import ClimateRange, Humidity, Temperature
from smart_home_backend.domain.value_objects.device import DeviceState

__all__ = [
    "ACTION_INTENTS",
    "READ_INTENTS",
    "RELAY_CHANNEL_COUNT",
    "AutomationSettings",
    "Capability",
    "ChannelConflictError",
    "ClarificationReason",
    "ClimateDemand",
    "ClimateRange",
    "ClimateReading",
    "CompletionBehavior",
    "ControlSource",
    "Device",
    "DeviceNotFoundError",
    "DeviceState",
    "DeviceStatus",
    "DeviceType",
    "DomainError",
    "HomeState",
    "Humidity",
    "Intent",
    "InvalidClimateValueError",
    "OperationStatus",
    "Relay",
    "RelayState",
    "Scenario",
    "ScenarioAction",
    "ScenarioStatus",
    "Sensor",
    "Temperature",
    "UnsupportedCapabilityError",
    "evaluate",
    "evaluate_humidity",
    "evaluate_temperature",
    "find_all_for_capability",
    "find_device_by_name",
    "find_device_for_capability",
    "has_timed_out",
    "is_goal_reached",
    "parse_capability",
    "parse_device_type",
]
