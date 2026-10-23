"""Переключить все устройства дома, которые это умеют."""

from __future__ import annotations

from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.domain.identifiers import UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.capability_report import CapabilityReport


class SwitchAllDevicesUseCase:
    """Применяет одну способность ко всем подходящим устройствам."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory, control: DeviceControlService) -> None:
        """Собирает сценарий переключения всего дома.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
            control: Сервис, доводящий способность до железа.
        """
        self._home_uow = home_uow
        self._control = control

    async def execute(self, user_id: UserId, capability: Capability) -> CapabilityReport:
        """Переключает каждое устройство, поддерживающее способность.

        Args:
            user_id: Владелец, разрешённый из сессии.
            capability: Способность, которую нужно выполнить.

        Returns:
            CapabilityReport: Устройства, которых это коснулось.
        """
        async with self._home_uow() as uow:
            devices = list(await uow.devices.list_all(user_id))
        return await self._control.apply_to_all(user_id, devices, capability)
