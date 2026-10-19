"""Device routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.domain.enums.device import parse_capability
from backend.domain.enums.operation import OperationStatus
from backend.presentation.api.errors import raise_for_status
from backend.presentation.api.messages import (
    channel_conflict_message,
    created_message,
    deleted_message,
    device_missing_message,
    not_found_message,
    unknown_mode_message,
    updated_message,
)
from backend.presentation.api.requests import (
    DeviceCreateBody,
    DeviceModeBody,
    DeviceUpdateBody,
)
from backend.presentation.api.responses import (
    DeviceResponse,
    ExecutionResponse,
    OperationResponse,
)
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
async def list_devices(
    container: AppContainer, user_id: CurrentUserId
) -> list[DeviceResponse]:
    """Return every configured device with its current status.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        list[DeviceResponse]: Configured devices.
    """
    devices = await container.get_devices.execute(user_id)
    runtime = container.runtimes.for_user(user_id)
    return [
        DeviceResponse.from_device(device, runtime.device_status(device).value)
        for device in devices
    ]


@router.get("/{device_id}")
async def get_device(
    device_id: int, container: AppContainer, user_id: CurrentUserId
) -> DeviceResponse:
    """Return one configured device.

    Args:
        device_id: Identifier of the device.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        DeviceResponse: The requested device.

    Raises:
        HTTPException: When the device does not exist.
    """
    device = await container.get_device.execute(user_id, device_id)
    if device is None:
        raise_for_status(OperationStatus.NOT_FOUND, not_found_message("Устройство", device_id))
    runtime = container.runtimes.for_user(user_id)
    return DeviceResponse.from_device(device, runtime.device_status(device).value)


@router.post("")
async def create_device(
    body: DeviceCreateBody, container: AppContainer, user_id: CurrentUserId
) -> OperationResponse:
    """Register a new logical device.

    Args:
        body: Device description.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: Result of the creation.

    Raises:
        HTTPException: When the relay channel is already taken.
    """
    status, device = await container.create_device.execute(user_id, body.to_command())
    runtime = container.runtimes.for_user(user_id)
    if status is OperationStatus.CHANNEL_CONFLICT:
        raise_for_status(status, channel_conflict_message(body.physical_channel))
    raise_for_status(status, created_message("Устройство", device.name))
    return OperationResponse(
        status=status.value,
        message=created_message("Устройство", device.name),
        data=DeviceResponse.from_device(
            device, runtime.device_status(device).value
        ).model_dump(),
    )


@router.patch("/{device_id}")
async def update_device(
    device_id: int,
    body: DeviceUpdateBody,
    container: AppContainer,
    user_id: CurrentUserId,
) -> OperationResponse:
    """Apply a partial update to a device.

    Args:
        device_id: Identifier of the device.
        body: Fields to change.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: Result of the update.

    Raises:
        HTTPException: When the device is missing or the channel is taken.
    """
    status, device = await container.update_device.execute(user_id, device_id, body.to_command())
    runtime = container.runtimes.for_user(user_id)
    if status is OperationStatus.CHANNEL_CONFLICT:
        raise_for_status(status, channel_conflict_message(body.physical_channel))
    raise_for_status(status, device_missing_message(device_id))
    return OperationResponse(
        status=status.value,
        message=updated_message("Устройство", device.name),
        data=DeviceResponse.from_device(
            device, runtime.device_status(device).value
        ).model_dump(),
    )


@router.delete("/{device_id}")
async def delete_device(
    device_id: int, container: AppContainer, user_id: CurrentUserId
) -> OperationResponse:
    """Remove a device.

    Args:
        device_id: Identifier of the device.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: Result of the deletion.

    Raises:
        HTTPException: When the device does not exist.
    """
    status = await container.delete_device.execute(user_id, device_id)
    message = deleted_message("Устройство", device_id)
    raise_for_status(status, message)
    return OperationResponse(status=status.value, message=message)


@router.post("/{device_id}/on")
async def turn_device_on(
    device_id: int, container: AppContainer, user_id: CurrentUserId
) -> ExecutionResponse:
    """Switch a device on.

    Args:
        device_id: Identifier of the device.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        ExecutionResponse: Result of the command.

    Raises:
        HTTPException: When the device is missing or cannot be controlled.
    """
    result = await container.turn_device_on.execute(user_id, device_id)
    raise_for_status(result.status, device_missing_message(device_id))
    return ExecutionResponse.from_execution(result)


@router.post("/{device_id}/off")
async def turn_device_off(
    device_id: int, container: AppContainer, user_id: CurrentUserId
) -> ExecutionResponse:
    """Switch a device off.

    Args:
        device_id: Identifier of the device.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        ExecutionResponse: Result of the command.

    Raises:
        HTTPException: When the device is missing or cannot be controlled.
    """
    result = await container.turn_device_off.execute(user_id, device_id)
    raise_for_status(result.status, device_missing_message(device_id))
    return ExecutionResponse.from_execution(result)


@router.post("/{device_id}/mode")
async def set_device_mode(
    device_id: int,
    body: DeviceModeBody,
    container: AppContainer,
    user_id: CurrentUserId,
) -> ExecutionResponse:
    """Switch a device into the requested mode.

    Args:
        device_id: Identifier of the device.
        body: Requested capability.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        ExecutionResponse: Result of the command.

    Raises:
        HTTPException: When the mode is unknown or the device cannot run it.
    """
    capability = parse_capability(body.mode)
    if capability is None:
        raise_for_status(OperationStatus.INVALID_INPUT, unknown_mode_message())
    result = await container.set_device_mode.execute(user_id, device_id, capability)
    raise_for_status(result.status, device_missing_message(device_id))
    return ExecutionResponse.from_execution(result)
