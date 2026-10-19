"""Mappers from domain objects to API payloads.

Mapping between layers lives in the presentation layer: use cases return domain
objects and the transport format is decided here.
"""

from __future__ import annotations

from typing import Any

from backend.application.dto.device import DeviceExecutionResult
from backend.domain.entities.automation import AutomationSettings
from backend.domain.entities.device import Device
from backend.domain.entities.home import ClimateReading
from backend.domain.entities.scenario import Scenario
from backend.domain.enums.operation import OperationStatus


def device_payload(device: Device, status: str) -> dict[str, Any]:
    """Return the API payload of a device.

    Args:
        device: Device to serialize.
        status: Current logical status of the device.

    Returns:
        dict[str, Any]: Serializable payload.
    """
    return {
        "id": device.id,
        "name": device.name,
        "type": device.type.value,
        "physical_channel": device.physical_channel,
        "capabilities": sorted(capability.value for capability in device.capabilities),
        "enabled": device.enabled,
        "automation_enabled": device.automation_enabled,
        "status": status,
    }


def automation_payload(settings: AutomationSettings) -> dict[str, Any]:
    """Return the API payload of the automation settings.

    Args:
        settings: Settings to serialize.

    Returns:
        dict[str, Any]: Serializable payload.
    """
    temperature_range = settings.temperature_range()
    humidity_range = settings.humidity_range()
    return {
        "enabled": settings.enabled,
        "target_temperature": settings.target_temperature,
        "min_temperature": temperature_range.low,
        "max_temperature": temperature_range.high,
        "target_humidity": settings.target_humidity,
        "min_humidity": humidity_range.low,
        "max_humidity": humidity_range.high,
        "participating_device_ids": sorted(settings.participating_device_ids),
    }


def scenario_payload(scenario: Scenario) -> dict[str, Any]:
    """Return the API payload of a scenario.

    Args:
        scenario: Scenario to serialize.

    Returns:
        dict[str, Any]: Serializable payload.
    """
    return {
        "id": scenario.id,
        "status": scenario.status.value,
        "created_at": scenario.created_at.isoformat(),
        "start_at": scenario.start_at.isoformat(),
        "duration_minutes": scenario.duration_minutes,
        "target": scenario.target,
        "actions": [action.to_dict() for action in scenario.actions],
        "completion_behavior": scenario.completion_behavior.value,
    }


def reading_payload(reading: ClimateReading) -> dict[str, Any]:
    """Return the API payload of a sensor reading.

    Args:
        reading: Reading to serialize.

    Returns:
        dict[str, Any]: Serializable payload.
    """
    temperature = reading.temperature
    humidity = reading.humidity
    return {
        "temperature": None if temperature is None else temperature.celsius,
        "humidity": None if humidity is None else humidity.percent,
    }


def execution_payload(result: DeviceExecutionResult) -> dict[str, Any]:
    """Return the API payload of a device command result.

    Args:
        result: Result to serialize.

    Returns:
        dict[str, Any]: Serializable payload.
    """
    device = result.device
    return {
        "status": result.status.value,
        "capability": None if result.capability is None else result.capability.value,
        "device": None
        if device is None
        else {
            "id": device.id,
            "name": device.name,
            "physical_channel": device.physical_channel,
        },
    }


def error_response(status: OperationStatus, detail: str) -> dict[str, Any]:
    """Return the API payload of a failed operation.

    Args:
        status: Result class of the operation.
        detail: Human readable reason.

    Returns:
        dict[str, Any]: Serializable payload.
    """
    return {"status": status.value, "detail": detail}
