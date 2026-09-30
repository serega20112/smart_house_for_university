"""Device routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from smart_home_backend.domain.enums.device import parse_capability
from smart_home_backend.domain.enums.operation import OperationStatus
from smart_home_backend.presentation.api.errors import raise_for_status
from smart_home_backend.presentation.api.messages import (
    channel_conflict_message,
    created_message,
    deleted_message,
    device_missing_message,
    not_found_message,
    unknown_mode_message,
    updated_message,
)
from smart_home_backend.presentation.api.requests import (
    DeviceCreateBody,
    DeviceModeBody,
    DeviceUpdateBody,
)
from smart_home_backend.presentation.api.responses import (
    DeviceResponse,
    ExecutionResponse,
    OperationResponse,
)
from smart_home_backend.presentation.dependencies import get_container

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
async def list_devices(request: Request) -> list[DeviceResponse]:
    """Return every configured device with its current status.

    Args:
        request: Incoming request carrying the dependency container.

    Returns:
        list[DeviceResponse]: Configured devices.
    """
    container = get_container(request)
    devices = await container.get_devices.execute()
    return [
        DeviceResponse.from_device(device, container.runtime.device_status(device).value)
        for device in devices
    ]


@router.get("/{device_id}")
async def get_device(device_id: int, request: Request) -> DeviceResponse:
    """Return one configured device.

    Args:
        device_id: Identifier of the device.
        request: Incoming request carrying the dependency container.

    Returns:
        DeviceResponse: The requested device.

    Raises:
        HTTPException: When the device does not exist.
    """
    container = get_container(request)
    device = await container.get_device.execute(device_id)
    if device is None:
        raise_for_status(OperationStatus.NOT_FOUND, not_found_message("Устройство", device_id))
    return DeviceResponse.from_device(device, container.runtime.device_status(device).value)


@router.post("")
async def create_device(body: DeviceCreateBody, request: Request) -> OperationResponse:
    """Register a new logical device.

    Args:
        body: Device description.
        request: Incoming request carrying the dependency container.

    Returns:
        OperationResponse: Result of the creation.

    Raises:
        HTTPException: When the relay channel is already taken.
    """
    container = get_container(request)
    status, device = await container.create_device.execute(body.to_command())
    if status is OperationStatus.CHANNEL_CONFLICT:
        raise_for_status(status, channel_conflict_message(body.physical_channel))
    raise_for_status(status, created_message("Устройство", device.name))
    return OperationResponse(
        status=status.value,
        message=created_message("Устройство", device.name),
        data=DeviceResponse.from_device(
            device, container.runtime.device_status(device).value
        ).model_dump(),
    )


@router.patch("/{device_id}")
async def update_device(
    device_id: int, body: DeviceUpdateBody, request: Request
) -> OperationResponse:
    """Apply a partial update to a device.

    Args:
        device_id: Identifier of the device.
        body: Fields to change.
        request: Incoming request carrying the dependency container.

    Returns:
        OperationResponse: Result of the update.

    Raises:
        HTTPException: When the device is missing or the channel is taken.
    """
    container = get_container(request)
    status, device = await container.update_device.execute(device_id, body.to_command())
    if status is OperationStatus.CHANNEL_CONFLICT:
        raise_for_status(status, channel_conflict_message(body.physical_channel))
    raise_for_status(status, device_missing_message(device_id))
    return OperationResponse(
        status=status.value,
        message=updated_message("Устройство", device.name),
        data=DeviceResponse.from_device(
            device, container.runtime.device_status(device).value
        ).model_dump(),
    )


@router.delete("/{device_id}")
async def delete_device(device_id: int, request: Request) -> OperationResponse:
    """Remove a device.

    Args:
        device_id: Identifier of the device.
        request: Incoming request carrying the dependency container.

    Returns:
        OperationResponse: Result of the deletion.

    Raises:
        HTTPException: When the device does not exist.
    """
    container = get_container(request)
    status = await container.delete_device.execute(device_id)
    message = deleted_message("Устройство", device_id)
    raise_for_status(status, message)
    return OperationResponse(status=status.value, message=message)


@router.post("/{device_id}/on")
async def turn_device_on(device_id: int, request: Request) -> ExecutionResponse:
    """Switch a device on.

    Args:
        device_id: Identifier of the device.
        request: Incoming request carrying the dependency container.

    Returns:
        ExecutionResponse: Result of the command.

    Raises:
        HTTPException: When the device is missing or cannot be controlled.
    """
    container = get_container(request)
    result = await container.turn_device_on.execute(device_id)
    raise_for_status(result.status, device_missing_message(device_id))
    return ExecutionResponse.from_execution(result)


@router.post("/{device_id}/off")
async def turn_device_off(device_id: int, request: Request) -> ExecutionResponse:
    """Switch a device off.

    Args:
        device_id: Identifier of the device.
        request: Incoming request carrying the dependency container.

    Returns:
        ExecutionResponse: Result of the command.

    Raises:
        HTTPException: When the device is missing or cannot be controlled.
    """
    container = get_container(request)
    result = await container.turn_device_off.execute(device_id)
    raise_for_status(result.status, device_missing_message(device_id))
    return ExecutionResponse.from_execution(result)


@router.post("/{device_id}/mode")
async def set_device_mode(
    device_id: int, body: DeviceModeBody, request: Request
) -> ExecutionResponse:
    """Switch a device into the requested mode.

    Args:
        device_id: Identifier of the device.
        body: Requested capability.
        request: Incoming request carrying the dependency container.

    Returns:
        ExecutionResponse: Result of the command.

    Raises:
        HTTPException: When the mode is unknown or the device cannot run it.
    """
    container = get_container(request)
    capability = parse_capability(body.mode)
    if capability is None:
        raise_for_status(OperationStatus.INVALID_INPUT, unknown_mode_message())
    result = await container.set_device_mode.execute(device_id, capability)
    raise_for_status(result.status, device_missing_message(device_id))
    return ExecutionResponse.from_execution(result)
