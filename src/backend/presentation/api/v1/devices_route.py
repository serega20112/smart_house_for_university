"""Device routes.

Routes translate interface bodies into application commands. What is allowed
to switch and what the board responds to is decided by application layer
scenarios, and device state is not guessed here: it is returned by the list
scenario.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from backend.application.use_cases.devices.create_device import CreateDeviceUseCase
from backend.application.use_cases.devices.delete_device import DeleteDeviceUseCase
from backend.application.use_cases.devices.list_devices import ListDevicesUseCase
from backend.application.use_cases.devices.switch_device import SwitchDeviceUseCase
from backend.application.use_cases.devices.update_device import UpdateDeviceUseCase
from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.devices.capability import Capability
from backend.presentation.api.requests.devices import (
    DeviceCreateBody,
    DeviceUpdateBody,
    create_command,
    update_command,
)
from backend.presentation.api.responses.devices import DeviceResponse, device_of
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    user_id: CurrentUserId,
    use_case: FromDishka[ListDevicesUseCase],
) -> list[DeviceResponse]:
    """Return all configured devices with their current state.

    Args:
        user_id: Owner authorised from bearer token.
        use_case: List devices with live state.

    Returns:
        list[DeviceResponse]: Configured devices.
    """
    return [device_of(device) for device in await use_case.execute(user_id)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeviceResponse)
async def create_device(
    body: DeviceCreateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[CreateDeviceUseCase],
) -> DeviceResponse:
    """Registers a new logical device.

    Args:
        body: Device description.
        user_id: Owner authorised from bearer token.
        use_case: Device creation.

    Returns:
        DeviceResponse: Created device.
    """
    device = await use_case.execute(user_id, create_command(body))
    return device_of(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    body: DeviceUpdateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[UpdateDeviceUseCase],
) -> DeviceResponse:
    """Applies a partial device change.

    Args:
        device_id: Device identifier.
        body: Fields to change.
        user_id: Owner authorised from bearer token.
        use_case: Device update.

    Returns:
        DeviceResponse: Updated device.
    """
    device = await use_case.execute(user_id, DeviceId.parse(device_id), update_command(body))
    return device_of(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    user_id: CurrentUserId,
    use_case: FromDishka[DeleteDeviceUseCase],
) -> None:
    """Deletes a device.

    Args:
        device_id: Device identifier.
        user_id: Owner authorised from bearer token.
        use_case: Device deletion.
    """
    await use_case.execute(user_id, DeviceId.parse(device_id))


@router.post("/{device_id}/capabilities/{capability}", response_model=DeviceResponse)
async def perform_capability(
    device_id: str,
    capability: str,
    user_id: CurrentUserId,
    use_case: FromDishka[SwitchDeviceUseCase],
) -> DeviceResponse:
    """Asks a device to perform a capability.

    Args:
        device_id: Device identifier.
        capability: Capability to perform.
        user_id: Owner authorised from bearer token.
        use_case: Switching a single device.

    Returns:
        DeviceResponse: Device in the state it reached.
    """
    device = await use_case.execute(
        user_id, DeviceId.parse(device_id), Capability.parse(capability)
    )
    return device_of(device)
