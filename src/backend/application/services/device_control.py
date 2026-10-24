"""Превращение способности в команду реле.

Через этот сервис идёт всякий путь, который меняет железо: человек в браузере, команда
в мессенджере, автоматика и сценарии — все. Поэтому правило живёт в одном месте, а не в
четырёх копиях.

Порядок шагов постоянен. Короткая транзакция читает конфигурацию и закрывается до того,
как попросят железо; плате приказывают, не держа транзакцию и не занимая соединение с
базой; подтверждение команды записывает дом изменчивого состояния; и только после этого
факт уходит интерфейсу и реакциям. Отклонённая команда поэтому оставляет события и
изменчивое состояние нетронутыми.

Текущее состояние устройства не живёт в строке конфигурации: его источник — сама плата,
поэтому оно хранится в доме изменчивого состояния. Второй записи строки после команды
нет, и версия конфигурации не растёт от щелчка реле: конфликт версий с чужой правкой
настроек уже не может отменить команду, которая выполнена физически.

Сервис не решает, что ручное действие значит для остальной системы. Ставить автоматику
на паузу — реакция, на которую подписываются другие компоненты; именно поэтому она
записана один раз.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.dto.boards.board_command_reason import BoardCommandReason
from backend.application.dto.views.capability_report import CapabilityFailure, CapabilityReport
from backend.application.dto.views.device_view import DeviceView
from backend.application.errors import (
    BoardNotChosenError,
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
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
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
            BoardNotChosenError: Когда устройство не привязано к плате, а плат несколько.
            BoardUnreachableError: Когда плата не подтвердила выполнение.
        """
        device = await self._load(user_id, device_id)
        return await self.apply_to_loaded(user_id, device, capability, manual=manual)

    async def apply_to_loaded(
        self,
        user_id: UserId,
        device: Device,
        capability: Capability,
        *,
        manual: bool = True,
    ) -> DeviceView:
        """Применяет способность к устройству, которое вызывающий уже прочитал.

        Так работают те, кто получил дом одним чтением: автоматика и сценарии не
        перечитывают выбранное устройство только ради того, чтобы сервис его увидел.

        Args:
            user_id: Владелец устройства и платы.
            device: Устройство, которое уже есть у вызывающего.
            capability: Способность, которую нужно выполнить.
            manual: Просил ли человек сам.

        Returns:
            DeviceView: Устройство с состоянием, которого оно достигло.

        Raises:
            NoDeviceForCapabilityError: Когда устройство этого не умеет.
            BoardNotChosenError: Когда устройство не привязано к плате, а плат несколько.
            BoardUnreachableError: Когда плата не подтвердила выполнение.
        """
        status = await self._perform(user_id, device, capability, manual)
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
            BoardNotChosenError: Когда устройство не привязано к плате, а плат несколько.
        """
        target = self._selector.first_supporting(devices, capability)
        if target is None:
            raise NoDeviceForCapabilityError(capability.value)
        return await self.apply_to_loaded(user_id, target, capability, manual=manual)

    async def apply_to_all(
        self,
        user_id: UserId,
        devices: Sequence[Device],
        capability: Capability,
        *,
        manual: bool = True,
    ) -> CapabilityReport:
        """Применяет способность к каждому устройству, которое её умеет.

        Плата, отказавшая в одной команде, не останавливает обход: отказ становится
        строкой отчёта, а не исключением посреди работы. Поэтому устройства,
        которые ответили, всё равно объявляются, а вызывающий получает и
        удавшиеся, и отказавшие с причинами. Устройство без платы в доме
        с несколькими платами попадает в отказ так же, как неответившее.

        Args:
            user_id: Владелец устройств и платы.
            devices: Устройства, к которым обращаются.
            capability: Способность, которую нужно выполнить.
            manual: Просил ли человек сам.

        Returns:
            CapabilityReport: Приведённые в действие устройства и отказы плат.
        """
        driven: list[tuple[Device, DeviceStatus]] = []
        failed: list[CapabilityFailure] = []
        for device in self._selector.all_supporting(devices, capability):
            try:
                status = await self._perform(user_id, device, capability, manual)
            except BoardUnreachableError as error:
                failed.append(
                    CapabilityFailure(device_id=device.id, name=device.name, reason=error.reason)
                )
                continue
            except BoardNotChosenError:
                failed.append(
                    CapabilityFailure(
                        device_id=device.id,
                        name=device.name,
                        reason=BoardCommandReason.BOARD_NOT_CHOSEN,
                    )
                )
                continue
            driven.append((device, status))
        for device, status in driven:
            await self._announce(user_id, device, status)
        return CapabilityReport(
            capability=capability,
            devices=tuple(DeviceView.of(device, status) for device, status in driven),
            failed=tuple(failed),
        )

    async def restore_statuses(
        self, user_id: UserId, targets: Sequence[tuple[Device, DeviceStatus]]
    ) -> None:
        """Возвращает устройства в состояния, в которых они были раньше.

        Список приходит готовым: вызывающий уже знает, какие устройства он переключил
        и какими они были, поэтому сервис не перебирает дом и не ищет нужные строки
        заново.

        Args:
            user_id: Владелец устройств и платы.
            targets: Устройства с состояниями, которые надо вернуть.
        """
        for device, status in targets:
            capability = DeviceStatus.restored_by(status)
            if capability is None:
                continue
            restored = await self._perform(user_id, device, capability, manual=False)
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
            BoardNotChosenError: Когда устройство не привязано к плате, а плат несколько.
            BoardUnreachableError: Когда плата не подтвердила выполнение.
        """
        device.require_capability(capability)
        board_id = await self._board_of(user_id, device)
        status = device.drive(capability, source_is_manual=manual)
        result = await self._boards.set_relay(
            user_id, board_id, int(device.channel), capability.energizes_relay
        )
        if not result.accepted:
            device.pull_events()
            raise BoardUnreachableError(result.reason or "unknown")

        await self._state_store.record_command_result(
            user_id,
            board_id,
            device.id,
            int(device.channel),
            status,
            self._clock.now(),
        )
        return status

    async def _board_of(self, user_id: UserId, device: Device) -> EspDeviceId:
        """Возвращает плату, которой адресована команда этого устройства.

        Привязанное устройство знает свою плату само. Непривязанному остаётся
        запасной путь только в доме с одной платой: при двух и более номер канала
        уже не говорит, на какой стороне дома он живёт, и угадывать нельзя.

        Args:
            user_id: Владелец устройства.
            device: Устройство, которому нужна плата.

        Returns:
            EspDeviceId: Плата, которой можно отдать команду.

        Raises:
            BoardNotChosenError: Когда плат в доме больше одной.
            BoardUnreachableError: Когда единственная плата не на связи.
        """
        if device.board_id is not None:
            return device.board_id
        async with self._home_uow() as uow:
            boards = await uow.boards.list_all(user_id)
        if len(boards) > 1:
            raise BoardNotChosenError()
        board_id = await self._boards.board_for(user_id)
        if board_id is None:
            raise BoardUnreachableError(BoardCommandReason.OFFLINE)
        return board_id

    async def _load(self, user_id: UserId, device_id: DeviceId) -> Device:
        """Читает устройство в короткой транзакции и сразу её закрывает.

        Args:
            user_id: Владелец устройства.
            device_id: Идентификатор устройства.

        Returns:
            Device: Снимок конфигурации, проверенный на существование.

        Raises:
            DeviceNotFoundError: Когда такого устройства у аккаунта нет.
        """
        async with self._home_uow() as uow:
            device = await uow.devices.get(user_id, device_id)
        if device is None:
            raise DeviceNotFoundError(device_id)
        return device

    async def _announce(self, user_id: UserId, device: Device, status: DeviceStatus) -> None:
        """Публикует факт после того, как подтверждение записано.

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
