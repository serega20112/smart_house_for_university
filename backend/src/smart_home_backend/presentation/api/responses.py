"""HTTP response schemas."""

from __future__ import annotations

from pydantic import BaseModel

from smart_home_backend.application.dto import CommandResult
from smart_home_backend.application.dto.device import DeviceExecutionResult
from smart_home_backend.application.use_cases.device import TurnAllResult
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.scenario import Scenario
from smart_home_backend.domain.enums.operation import OperationStatus
from smart_home_backend.presentation.api import mappers
from smart_home_backend.presentation.api.messages import (
    automation_toggled_message,
    command_message,
    execution_message,
    settings_saved_message,
    turn_all_message,
)


class DeviceResponse(BaseModel):
    """A device as returned by the API."""

    id: int
    name: str
    type: str
    physical_channel: int
    capabilities: list[str]
    enabled: bool
    automation_enabled: bool
    status: str

    @classmethod
    def from_device(cls, device: Device, status: str) -> "DeviceResponse":
        """Build the response from a domain device.

        Args:
            device: Device to serialize.
            status: Current logical status of the device.

        Returns:
            DeviceResponse: API representation.
        """
        return cls(**mappers.device_payload(device, status))

    @classmethod
    def from_devices(cls, devices: list[Device], statuses: dict[int, str]) -> list["DeviceResponse"]:
        """Build responses for a list of devices.

        Args:
            devices: Devices to serialize.
            statuses: Device identifiers mapped to their status.

        Returns:
            list[DeviceResponse]: API representations.
        """
        return [cls.from_device(device, statuses.get(device.id, "OFF")) for device in devices]


class AutomationResponse(BaseModel):
    """Automation settings as returned by the API."""

    enabled: bool
    target_temperature: float
    min_temperature: float
    max_temperature: float
    target_humidity: float
    min_humidity: float
    max_humidity: float
    participating_device_ids: list[int]

    @classmethod
    def from_settings(cls, settings: AutomationSettings) -> "AutomationResponse":
        """Build the response from domain settings.

        Args:
            settings: Settings to serialize.

        Returns:
            AutomationResponse: API representation.
        """
        return cls(**mappers.automation_payload(settings))


class ScenarioResponse(BaseModel):
    """A scenario as returned by the API."""

    id: int
    status: str
    created_at: str
    start_at: str
    duration_minutes: int | None
    target: str | None
    actions: list[dict]
    completion_behavior: str

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> "ScenarioResponse":
        """Build the response from a domain scenario.

        Args:
            scenario: Scenario to serialize.

        Returns:
            ScenarioResponse: API representation.
        """
        return cls(**mappers.scenario_payload(scenario))


class OperationResponse(BaseModel):
    """Generic result of a mutating request."""

    status: str
    message: str
    data: dict | None = None


class ExecutionResponse(BaseModel):
    """Result of a device command."""

    status: str
    message: str
    device: dict | None = None
    capability: str | None = None

    @classmethod
    def from_execution(cls, result: DeviceExecutionResult) -> "ExecutionResponse":
        """Build the response from a device command result.

        Args:
            result: Result to serialize.

        Returns:
            ExecutionResponse: API representation.
        """
        payload = mappers.execution_payload(result)
        return cls(message=execution_message(result), **payload)

    @classmethod
    def from_turn_all(cls, result: TurnAllResult, on: bool) -> "ExecutionResponse":
        """Build the response from a switch all result.

        Args:
            result: Result to serialize.
            on: Whether the devices were switched on.

        Returns:
            ExecutionResponse: API representation.
        """
        status = OperationStatus.SUCCESS if result.switched else OperationStatus.UNSUPPORTED
        return cls(status=status.value, message=turn_all_message(result, on))


class HomeStateResponse(BaseModel):
    """Full snapshot of the home state."""

    backend_online: bool
    esp_online: bool
    manual_override: bool
    temperature: float | None
    humidity: float | None
    devices: list[DeviceResponse]
    automation: AutomationResponse
    active_scenarios: list[ScenarioResponse]


class CommandResponse(BaseModel):
    """Answer to a free-form command."""

    status: str
    intent: str | None
    confidence: float
    message: str
    requires_clarification: bool
    clarification: str | None
    scenario_id: int | None

    @classmethod
    def from_result(cls, result: CommandResult) -> "CommandResponse":
        """Build the response from a structured command result.

        Args:
            result: Result to serialize.

        Returns:
            CommandResponse: API representation.
        """
        return cls(
            status=result.status.value,
            intent=result.intent,
            confidence=result.confidence,
            message=command_message(result),
            requires_clarification=result.clarification is not None,
            clarification=None if result.clarification is None else result.clarification.value,
            scenario_id=result.scenario_id,
        )


class SettingsResponse(BaseModel):
    """Answer of a settings update request."""

    status: str
    message: str
    automation: AutomationResponse


def settings_saved_response(settings: AutomationSettings) -> SettingsResponse:
    """Return the response of a settings update request.

    Args:
        settings: Stored settings.

    Returns:
        SettingsResponse: API representation.
    """
    return SettingsResponse(
        status=OperationStatus.SUCCESS.value,
        message=settings_saved_message(),
        automation=AutomationResponse.from_settings(settings),
    )


def automation_toggled_response(
    settings: AutomationSettings, enabled: bool
) -> SettingsResponse:
    """Return the response of a toggled automation mode.

    Args:
        settings: Stored settings.
        enabled: Desired state of the automation mode.

    Returns:
        SettingsResponse: API representation.
    """
    return SettingsResponse(
        status=OperationStatus.SUCCESS.value,
        message=automation_toggled_message(enabled),
        automation=AutomationResponse.from_settings(settings),
    )
