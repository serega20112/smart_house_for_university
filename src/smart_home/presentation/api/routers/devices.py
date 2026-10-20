"""Device routes.

The routes only translate between the bodies of the interface and the commands
of the application. Every decision about what may be switched and what a board
answers belongs to the use cases, and the status of a device is never guessed
here: it is read from the live state of the home.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from smart_home.application.dto import (
    Capability,
    CreateDeviceCommand,
    DeviceId,
    UpdateDeviceCommand,
)
from smart_home.application.ports.queries.devices import DeviceQueries
from smart_home.application.ports.services import HomeStateStore
from smart_home.application.use_cases.devices.create_device import CreateDeviceUseCase
from smart_home.application.use_cases.devices.delete_device import DeleteDeviceUseCase
from smart_home.application.use_cases.devices.switch_device import SwitchDeviceUseCase
from smart_home.application.use_cases.devices.update_device import UpdateDeviceUseCase
from smart_home.presentation.api.schemas import (
    DeviceCreateBody,
    DeviceResponse,
    DeviceUpdateBody,
    device_of,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    user_id: CurrentUserId,
    queries: FromDishka[DeviceQueries],
    state_store: FromDishka[HomeStateStore],
) -> list[DeviceResponse]:
    """Return every configured device with its current status.

    Args:
        user_id: Owner resolved from the bearer token.
        queries: Reads of the device configuration.
        state_store: Durable home of the volatile state.

    Returns:
        list[DeviceResponse]: Configured devices.
    """
    devices = await queries.list_all(user_id)
    state = await state_store.read(user_id)
    return [
        device_of(device.with_status(state.status_for(device.id, device.channel)))
        for device in devices
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeviceResponse)
async def create_device(
    body: DeviceCreateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[CreateDeviceUseCase],
) -> DeviceResponse:
    """Register a new logical device.

    Args:
        body: Device description.
        user_id: Owner resolved from the bearer token.
        use_case: Device creation.

    Returns:
        DeviceResponse: The created device.
    """
    device = await use_case.execute(
        user_id,
        CreateDeviceCommand(
            name=body.name,
            kind=body.kind,
            channel=body.channel,
            capabilities=frozenset(body.capabilities),
            enabled=body.enabled,
            automation_enabled=body.automation_enabled,
        ),
    )
    return device_of(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    body: DeviceUpdateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[UpdateDeviceUseCase],
) -> DeviceResponse:
    """Apply a partial update to a device.

    Args:
        device_id: Identifier of the device.
        body: Fields to change.
        user_id: Owner resolved from the bearer token.
        use_case: Device change.

    Returns:
        DeviceResponse: The updated device.
    """
    device = await use_case.execute(
        user_id,
        DeviceId.parse(device_id),
        UpdateDeviceCommand(
            name=body.name,
            kind=body.kind,
            channel=body.channel,
            capabilities=None if body.capabilities is None else frozenset(body.capabilities),
            enabled=body.enabled,
            automation_enabled=body.automation_enabled,
        ),
    )
    return device_of(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    user_id: CurrentUserId,
    use_case: FromDishka[DeleteDeviceUseCase],
) -> None:
    """Remove a device.

    Args:
        device_id: Identifier of the device.
        user_id: Owner resolved from the bearer token.
        use_case: Device removal.

    Returns:
        None.
    """
    await use_case.execute(user_id, DeviceId.parse(device_id))


@router.post("/{device_id}/capabilities/{capability}", response_model=DeviceResponse)
async def perform_capability(
    device_id: str,
    capability: str,
    user_id: CurrentUserId,
    use_case: FromDishka[SwitchDeviceUseCase],
) -> DeviceResponse:
    """Ask a device to perform a capability.

    Args:
        device_id: Identifier of the device.
        capability: Capability to perform.
        user_id: Owner resolved from the bearer token.
        use_case: Switch of one device.

    Returns:
        DeviceResponse: The device with the status it reached.
    """
    device = await use_case.execute(
        user_id,
        DeviceId.parse(device_id),
        Capability.parse(capability),
    )
    return device_of(device)
