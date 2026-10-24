"""Убирает логическое устройство."""

from __future__ import annotations

from backend.application.errors import DeviceNotFoundError
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.events import EventName
from backend.domain.identifiers import DeviceId, UserId


class DeleteDeviceUseCase:
    """Удаляет устройство и забывает всё, что о нём знал исполняющий слой."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
    ) -> None:
        """Инициализирует сценарий.

        Args:
            home_uow: Фабрика транзакций над конфигурацией.
            state_store: Надёжный дом изменчивого состояния.
            realtime: Издатель событий в открытые соединения.
        """
        self._home_uow = home_uow
        self._state_store = state_store
        self._realtime = realtime

    async def execute(self, user_id: UserId, device_id: DeviceId) -> None:
        """Удаляет устройство.

        Args:
            user_id: Владелец, разрешённый из сессии.
            device_id: Идентификатор устройства.

        Raises:
            DeviceNotFoundError: Когда такого устройства у аккаунта нет.
        """
        async with self._home_uow() as uow:
            removed = await uow.devices.delete(user_id, device_id)
            if removed:
                await uow.commit()
        if not removed:
            raise DeviceNotFoundError(device_id)
        await self._state_store.forget_device_status(user_id, device_id)
        await self._realtime.publish(
            user_id, EventName.DEVICES_UPDATED, {"deleted": str(device_id)}
        )
