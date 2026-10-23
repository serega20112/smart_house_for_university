"""Переключить одно устройство по названному идентификатору."""

from __future__ import annotations

from backend.application.services.device_control import DeviceControlService
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_view import DeviceView


class SwitchDeviceUseCase:
    """Применяет одну способность к одному устройству.

    Включение, выключение и перевод в режим — одна и та же операция с разной
    способностью, поэтому сценарий один, а не три его копии.
    """

    def __init__(self, control: DeviceControlService) -> None:
        """Собирает сценарий переключения устройства.

        Args:
            control: Сервис, доводящий способность до железа.
        """
        self._control = control

    async def execute(
        self, user_id: UserId, device_id: DeviceId, capability: Capability
    ) -> DeviceView:
        """Переключает устройство.

        Args:
            user_id: Владелец, разрешённый из сессии.
            device_id: Идентификатор устройства.
            capability: Способность, которую нужно выполнить.

        Returns:
            DeviceView: Устройство в том состоянии, которого оно достигло.

        Raises:
            DeviceNotFoundError: Когда у аккаунта нет такого устройства.
            UnsupportedCapabilityError: Когда устройство этого не умеет.
            BoardUnreachableError: Когда плата не подтвердила команду.
        """
        return await self._control.apply_to_device(user_id, device_id, capability)
