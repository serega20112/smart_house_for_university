"""Меняет уже существующее логическое устройство."""

from __future__ import annotations

from backend.application.dto.devices.update_device_command import UpdateDeviceCommand
from backend.application.errors import (
    ConcurrentModificationError,
    DeviceNotFoundError,
)
from backend.application.interface.services.domain_event_dispatcher import DomainEventDispatcher
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.device.device import Device
from backend.domain.events import EventName
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.devices.device_view import DeviceView
from backend.domain.value_objects.devices.relay_channel import RelayChannel


class UpdateDeviceUseCase:
    """Применяет частичное изменение устройства."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        state_store: HomeStateStore,
        refresh_attempts: int,
    ) -> None:
        """Инициализирует сценарий.

        Args:
            home_uow: Фабрика транзакций над конфигурацией.
            realtime: Издатель событий в открытые соединения.
            dispatcher: Объявляет факт изменения конфигурации.
            state_store: Надёжный дом изменчивого состояния.
            refresh_attempts: Сколько раз повторить изменение после проигранной гонки.
        """
        self._home_uow = home_uow
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._state_store = state_store
        self._refresh_attempts = refresh_attempts

    async def execute(
        self, user_id: UserId, device_id: DeviceId, command: UpdateDeviceCommand
    ) -> DeviceView:
        """Меняет устройство по свежему снимку конфигурации.

        Поиск ограничен владельцем, поэтому чужое устройство читается как
        отсутствующее, а не изменяется. Изменение, проигравшее гонку другому
        записывающему, повторяется по самому новому снимку, чтобы человеку не
        приходилось повторять себя из-за другой вкладки, тронувшей то же устройство.

        Args:
            user_id: Владелец, разрешённый из сессии.
            device_id: Идентификатор устройства.
            command: Поля, которые нужно изменить.

        Returns:
            DeviceView: Обновлённое устройство.

        Raises:
            DeviceNotFoundError: Когда такого устройства у аккаунта нет.
            ChannelConflictError: Когда новый канал уже занят.
            ConcurrentModificationError: Когда гонку продолжают выигрывать другие.
        """
        stored: Device | ConcurrentModificationError = await self._attempt(
            user_id, device_id, command
        )
        for _ in range(self._refresh_attempts - 1):
            if not isinstance(stored, ConcurrentModificationError):
                break
            stored = await self._attempt(user_id, device_id, command)
        if isinstance(stored, ConcurrentModificationError):
            raise stored
        device = stored
        await self._realtime.publish(
            user_id, EventName.DEVICES_UPDATED, {"updated": str(device_id)}
        )
        await self._dispatcher.dispatch(device.pull_events())
        state = await self._state_store.read(user_id)
        return DeviceView.of(device, state.status_of(device))

    async def _attempt(
        self, user_id: UserId, device_id: DeviceId, command: UpdateDeviceCommand
    ) -> Device | ConcurrentModificationError:
        """Заявляет изменение один раз на снимке, который читает транзакция.

        Args:
            user_id: Владелец, разрешённый из сессии.
            device_id: Идентификатор устройства.
            command: Поля, которые нужно изменить.

        Returns:
            Device | ConcurrentModificationError: Обновлённое устройство или гонка,
            которую эта попытка проиграла.
        """
        async with self._home_uow() as uow:
            device = await uow.devices.get(user_id, device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)
            try:
                device.reconfigure(
                    name=command.name,
                    kind=command.kind,
                    channel=(None if command.channel is None else RelayChannel(command.channel)),
                    capabilities=command.capabilities,
                    enabled=command.enabled,
                    automation_enabled=command.automation_enabled,
                )
                device.record_change()
                await uow.devices.update(device)
            except ConcurrentModificationError as lost:
                return lost
            return device
