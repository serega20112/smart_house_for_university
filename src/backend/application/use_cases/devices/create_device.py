"""Добавляет новое логическое устройство.

Raises:
    ChannelConflictError: Когда канал реле уже подключён к другому устройству
        того же аккаунта.
    BoardNotFoundError: Когда плата, на которую ставят устройство, не принадлежит
        аккаунту.
"""

from __future__ import annotations

from backend.application.dto.devices.create_device_command import CreateDeviceCommand
from backend.application.dto.views.device_view import DeviceView
from backend.application.errors import BoardNotFoundError
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWork, HomeUnitOfWorkFactory
from backend.domain.aggregates.device.device import Device
from backend.domain.events import EventName
from backend.domain.identifiers import UserId
from backend.domain.value_objects.devices.relay_channel import RelayChannel


class CreateDeviceUseCase:
    """Добавляет устройство на свободный канал реле."""

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

        Плата приходит от клиента, поэтому прикладной слой сам проверяет, что она
        принадлежит этому аккаунту: чужая плата читается как отсутствующая, и
        устройство на ней не появляется.

        Args:
            user_id: Владелец, разрешённый из сессии.
            command: Описание устройства.

        Returns:
            DeviceView: Созданное устройство с текущим состоянием из изменчивого дома.

        Raises:
            BoardNotFoundError: Когда плата не принадлежит аккаунту.
            ChannelConflictError: Когда канал реле уже подключён к другому устройству
                того же аккаунта.
        """
        async with self._home_uow() as uow:
            await self._require_board(uow, user_id, command)
            device = Device.create(
                user_id=user_id,
                name=command.name,
                kind=command.kind,
                channel=RelayChannel(command.channel),
                capabilities=command.capabilities,
                board_id=command.board_id,
                enabled=command.enabled,
                automation_enabled=command.automation_enabled,
            )
            device.record_change()
            await uow.devices.add(device)
            await uow.commit()
        await self._realtime.publish(
            user_id,
            EventName.DEVICES_UPDATED,
            {"created": str(device.id), "name": device.name},
        )
        await self._dispatcher.dispatch(device.pull_events())
        state = await self._state_store.read(user_id)
        return DeviceView.of(device, state.status_of(device))

    async def _require_board(
        self, uow: HomeUnitOfWork, user_id: UserId, command: CreateDeviceCommand
    ) -> None:
        """Проверяет, что плата устройства принадлежит аккаунту.

        Args:
            uow: Транзакция, в которой создают устройство.
            user_id: Владелец, разрешённый из сессии.
            command: Описание устройства.

        Raises:
            BoardNotFoundError: Когда плата не принадлежит аккаунту.
        """
        if command.board_id is None:
            return
        board = await uow.boards.get(user_id, command.board_id)
        if board is None:
            raise BoardNotFoundError(command.board_id)
