"""Превращение способности в команду реле.

Через этот сервис идёт всякий путь, который меняет железо: человек в браузере, команда
в мессенджере, автоматика и сценарии — все. Поэтому правило живёт в одном месте, а не в
четырёх копиях.

Порядок шагов постоянен. Агрегат загружают и транзакцию закрывают до того, как
попросят железо; плате приказывают, не держая соединение с базой; затем свежая короткая
транзакция сохраняет подтверждённое состояние; и только после её коммита факт уходит
интерфейсу и реакциям. Отклонённая команда поэтому оставляет базу, события и изменчивое
состояние нетронутыми.

Сервис не решает, что ручное действие значит для остальной системы. Ставить автоматику
на паузу — реакция, на которую подписываются другие компоненты; именно поэтому она
записана один раз.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.dto.views.capability_report import CapabilityReport
from backend.application.dto.views.device_view import DeviceView
from backend.application.errors import (
    BoardUnreachableError,
    DeviceNotFoundError,
    NoDeviceForCapabilityError,
)
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.device.device import Device
from backend.domain.events import EventName
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.policies.device_selector import DeviceSelector
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_status import DeviceStatus


class DeviceControlService:
    """Применяет способности к устройствам и держит состояние в ладу с ними."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        boards: BoardGateway,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        clock: Clock,
        selector: DeviceSelector,
    ) -> None:
        """Инициализирует сервис.

        Args:
            home_uow: Фабрика транзакций над конфигурацией.
            boards: Шлюз к физическому железу.
            state_store: Надёжный дом изменчивого состояния.
            realtime: Издатель событий в открытые соединения.
            dispatcher: Отдаёт записанные факты подписанным на них.
            clock: Источник текущего времени.
            selector: Находит устройства по способности.
        """
        self._home_uow = home_uow
        self._boards = boards
        self._state_store = state_store
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._clock = clock
        self._selector = selector

    async def apply_to_device(
        self,
        user_id: UserId,
        device_id: DeviceId,
        capability: Capability,
        *,
        manual: bool = True,
    ) -> DeviceView:
        """Применяет способность к одному устройству.

        Args:
            user_id: Владелец устройства и платы.
            device_id: Идентификатор устройства.
            capability: Способность, которую нужно выполнить.
            manual: Просил ли человек сам.

        Returns:
            DeviceView: Устройство с состоянием, которого оно достигло.

        Raises:
            DeviceNotFoundError: Когда такого устройства у аккаунта нет.
            NoDeviceForCapabilityError: Когда устройство этого не умеет.
            BoardUnreachableError: Когда плата не подтвердила выполнение.
        """
        async with self._home_uow() as uow:
            device = await uow.devices.get(user_id, device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)

        status = await self._perform(user_id, device, capability, manual)
        await self._persist(user_id, device)
        await self._announce(user_id, device, status)
        return DeviceView.of(device, status)

    async def apply_to_first_matching(
        self,
        user_id: UserId,
        devices: Sequence[Device],
        capability: Capability,
        *,
        manual: bool = True,
    ) -> DeviceView:
        """Применяет способность к первому устройству, которое её умеет.

        Args:
            user_id: Владелец устройств и платы.
            devices: Подходящие кандидаты.
            capability: Способность, которую нужно выполнить.
            manual: Просил ли человек сам.

        Returns:
            DeviceView: Устройство, которое привели в действие.

        Raises:
            NoDeviceForCapabilityError: Когда в доме этого не умеет никто.
        """
        target = self._selector.first_supporting(devices, capability)
        if target is None:
            raise NoDeviceForCapabilityError(capability.value)
        status = await self._perform(user_id, target, capability, manual)
        await self._persist(user_id, target)
        await self._announce(user_id, target, status)
        return DeviceView.of(target, status)

    async def apply_to_all(
        self,
        user_id: UserId,
        devices: Sequence[Device],
        capability: Capability,
        *,
        manual: bool = True,
    ) -> CapabilityReport:
        """Применяет способность к каждому устройству, которое её умеет.

        Плата, отказавшая в одной команде, не останавливает остальные: вызывающий
        получает отчёт о том, что было приведено в действие, — это полезнее исключения
        посреди обхода.

        Args:
            user_id: Владелец устройств и платы.
            devices: Устройства, к которым обращаются.
            capability: Способность, которую нужно выполнить.
            manual: Просил ли человек сам.

        Returns:
            CapabilityReport: Устройства, приведённые в действие.
        """
        driven: list[tuple[Device, DeviceStatus]] = []
        for device in self._selector.all_supporting(devices, capability):
            status = await self._perform(user_id, device, capability, manual)
            driven.append((device, status))
        await self._persist(user_id, *(device for device, _status in driven))
        for device, status in driven:
            await self._announce(user_id, device, status)
        return CapabilityReport(
            capability=capability,
            devices=tuple(DeviceView.of(device, status) for device, status in driven),
        )

    async def restore_statuses(
        self, user_id: UserId, devices: Sequence[Device], wanted: dict[DeviceId, DeviceStatus]
    ) -> None:
        """Возвращает устройства в состояния, в которых они были раньше.

        Args:
            user_id: Владелец устройств и платы.
            devices: Устройства, к которым обращаются.
            wanted: Желаемое состояние для каждого устройства.
        """
        by_id = {device.id: device for device in devices}
        for device_id, status in wanted.items():
            device = by_id.get(device_id)
            capability = DeviceStatus.restored_by(status)
            if device is None or capability is None:
                continue
            restored = await self._perform(user_id, device, capability, manual=False)
            await self._persist(user_id, device)
            await self._announce(user_id, device, restored)

    async def views_with_live_status(
        self, user_id: UserId, devices: Sequence[Device]
    ) -> list[DeviceView]:
        """Возвращает устройства с состоянием, которое у них сейчас.

        Args:
            user_id: Владелец устройств.
            devices: Настроенные устройства.

        Returns:
            list[DeviceView]: Устройства с их живым состоянием.
        """
        state = await self._state_store.read(user_id)
        return [DeviceView.of(device, state.status_of(device)) for device in devices]

    async def _perform(
        self,
        user_id: UserId,
        device: Device,
        capability: Capability,
        manual: bool,
    ) -> DeviceStatus:
        """Решает и приводит в действие, не держа транзакцию, пока плата отвечает.

        Args:
            user_id: Владелец платы.
            device: Устройство, на котором выполняют способность.
            capability: Способность, которую нужно выполнить.
            manual: Просил ли человек сам.

        Returns:
            DeviceStatus: Состояние, которого устройство достигло.

        Raises:
            UnsupportedCapabilityError: Когда устройство этого не умеет.
            BoardUnreachableError: Когда плата не подтвердила выполнение.
        """
        device.require_capability(capability)
        board_id = device.board_id
        if board_id is None:
            board_id = await self._boards.board_for(user_id)
        if board_id is None:
            raise BoardUnreachableError("esp_offline")
        status = device.drive(capability, source_is_manual=manual)
        result = await self._boards.set_relay(
            user_id, board_id, int(device.channel), capability.energizes_relay
        )
        if not result.accepted:
            device.pull_events()
            raise BoardUnreachableError(result.reason or "unknown")

        await self._state_store.record_command_result(user_id, device, status, self._clock.now())
        return status

    async def _persist(self, user_id: UserId, *devices: Device) -> None:
        """Сохраняет агрегаты в одной короткой транзакции.

        Args:
            user_id: Владелец устройств.
            devices: Агрегаты для сохранения; каждый уже подтверждён платой.
        """
        async with self._home_uow() as uow:
            for device in devices:
                await uow.devices.update(device)
            await uow.commit()

    async def _announce(self, user_id: UserId, device: Device, status: DeviceStatus) -> None:
        """Публикует факт, когда он закоммичен.

        Args:
            user_id: Владелец устройства.
            device: Устройство, к которому относится факт.
            status: Состояние, в которое устройство привели.
        """
        await self._realtime.publish(
            user_id,
            EventName.DEVICE_STATE_CHANGED,
            {
                "device_id": str(device.id),
                "name": device.name,
                "channel": int(device.channel),
                "status": status.value,
            },
        )
        await self._dispatcher.dispatch(device.pull_events())
