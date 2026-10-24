"""Меняет уже существующее логическое устройство."""

from __future__ import annotations

from backend.application.dto.devices.update_device_command import UpdateDeviceCommand
from backend.application.dto.views.device_view import DeviceView
from backend.application.errors import (
    ConcurrentModificationError,
    DeviceNotFoundError,
)
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.device.device import Device
from backend.domain.events import EventName
from backend.domain.identifiers import DeviceId, UserId
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
        device = await self._apply_repeated(user_id, device_id, command)
        await self._realtime.publish(
            user_id, EventName.DEVICES_UPDATED, {"updated": str(device_id)}
        )
        await self._dispatcher.dispatch(device.pull_events())
        state = await self._state_store.read(user_id)
        return DeviceView.of(device, state.status_of(device))

    async def _apply_repeated(
        self, user_id: UserId, device_id: DeviceId, command: UpdateDeviceCommand
    ) -> Device:
        """Повторяет изменение по свежему снимку, пока гонку не удастся выиграть.

        Каждое повторение — отдельная короткая транзакция: проиграв запись, сценарий
        откатывает её и перечитывает устройство заново, а не перетирает то, что успел
        изменить другой. Исчерпав попытки, бросает честную ошибку с настоящим
        идентификатором устройства.

        Args:
            user_id: Владелец, разрешённый из сессии.
            device_id: Идентификатор устройства.
            command: Поля, которые нужно изменить.

        Returns:
            Device: Обновлённое устройство.

        Raises:
            ConcurrentModificationError: Когда гонку продолжают выигрывать другие.
        """
        for _ in range(max(1, self._refresh_attempts)):
            try:
                return await self._apply_once(user_id, device_id, command)
            except ConcurrentModificationError:
                continue
        raise ConcurrentModificationError("device", device_id)

    async def _apply_once(
        self, user_id: UserId, device_id: DeviceId, command: UpdateDeviceCommand
    ) -> Device:
        """Заявляет изменение один раз на снимке, который читает транзакция.

        Args:
            user_id: Владелец, разрешённый из сессии.
            device_id: Идентификатор устройства.
            command: Поля, которые нужно изменить.

        Returns:
            Device: Обновлённое устройство.

        Raises:
            DeviceNotFoundError: Когда такого устройства у аккаунта нет.
            ConcurrentModificationError: Когда запись проиграла гонку.
        """
        async with self._home_uow() as uow:
            device = await uow.devices.get(user_id, device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)
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
            await uow.commit()
            return device
