"""Маршруты устройств.

Маршрут переводит тело запроса в команду приложения. Что можно включить и на что
ответит плата, решают сценарии прикладного слоя, и состояние устройства здесь не
угадывается: его возвращает тот же сценарий, который его получил.
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
    """Возвращает все настроенные устройства с их текущим состоянием.

    Args:
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Список устройств вместе с живым состоянием.

    Returns:
        list[DeviceResponse]: Настроенные устройства.
    """
    return [device_of(device) for device in await use_case.execute(user_id)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeviceResponse)
async def create_device(
    body: DeviceCreateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[CreateDeviceUseCase],
) -> DeviceResponse:
    """Заводит новое логическое устройство.

    Args:
        body: Описание устройства.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Создание устройства.

    Returns:
        DeviceResponse: Созданное устройство.
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
    """Применяет частичное изменение устройства.

    Args:
        device_id: Идентификатор устройства.
        body: Поля, которые нужно изменить.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Изменение устройства.

    Returns:
        DeviceResponse: Изменённое устройство.
    """
    device = await use_case.execute(user_id, DeviceId.parse(device_id), update_command(body))
    return device_of(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    user_id: CurrentUserId,
    use_case: FromDishka[DeleteDeviceUseCase],
) -> None:
    """Удаляет устройство.

    Args:
        device_id: Идентификатор устройства.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Удаление устройства.
    """
    await use_case.execute(user_id, DeviceId.parse(device_id))


@router.post("/{device_id}/capabilities/{capability}", response_model=DeviceResponse)
async def perform_capability(
    device_id: str,
    capability: str,
    user_id: CurrentUserId,
    use_case: FromDishka[SwitchDeviceUseCase],
) -> DeviceResponse:
    """Просит устройство выполнить способность.

    Args:
        device_id: Идентификатор устройства.
        capability: Способность, которую просят выполнить.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Переключение одного устройства.

    Returns:
        DeviceResponse: Устройство в том состоянии, которого оно достигло.
    """
    device = await use_case.execute(
        user_id, DeviceId.parse(device_id), Capability.parse(capability)
    )
    return device_of(device)
