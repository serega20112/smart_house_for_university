"""Заводит новое логическое устройство."""

from __future__ import annotations

from backend.application.dto.devices.create_device_command import CreateDeviceCommand
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.device.device import Device
from backend.domain.events import EventName
from backend.domain.identifiers import UserId
from backend.domain.value_objects.devices.device_view import DeviceView
from backend.domain.value_objects.devices.relay_channel import RelayChannel


class CreateDeviceUseCase:
    """Добавляет устройство, привязанное к свободному каналу реле платы."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        state_store: HomeStateStore,
    ) -> None:
        """Инициализирует сценарий.

        Args:
            home_uow: Фабрика транзакций над конфигурацией.
            realtime: Издатель событий в открытые соединения.
            dispatcher: Объявляет факт изменения конфигурации.
            state_store: Надёжный дом изменчивого состояния.
        """
        self._home_uow = home_uow
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._state_store = state_store

    async def execute(self, user_id: UserId, command: CreateDeviceCommand) -> DeviceView:
        """Добавляет устройство.

        Args:
            user_id: Владелец, разрешённый из сессии.
            command: Описание устройства.

        Returns:
            DeviceView: Созданное устройство с состоянием, которое об нём знает
            изменчивое состояние прямо сейчас.

        Raises:
            ChannelConflictError: Когда канал реле уже подключён к другому устройству
            того же аккаунта.
        """
        async with self._home_uow() as uow:
            device = Device.create(
                user_id=user_id,
                name=command.name,
                kind=command.kind,
                channel=RelayChannel(command.channel),
                capabilities=command.capabilities,
                enabled=command.enabled,
                automation_enabled=command.automation_enabled,
            )
            device.record_change()
            await uow.devices.add(device)
        await self._realtime.publish(
            user_id,
            EventName.DEVICES_UPDATED,
            {"created": str(device.id), "name": device.name},
        )
        await self._dispatcher.dispatch(device.pull_events())
        state = await self._state_store.read(user_id)
        return DeviceView.of(device, state.status_of(device))
