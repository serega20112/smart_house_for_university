"""
Живое состояние одного дома, снятое с его плат.

Это состояние аккаунта, а не самостоятельный корень: дочерних сущностей у него
нет — положения каналов, показания климата, доступность плат, приказанные режимы и
окно ручного управления. Состояние детерминировано: часы он не читает, момент
приносит вызывающий.

Дом живёт на нескольких платах, и всё физическое ключуется платой: канал 1 первой
платы и канал 1 второй — разные контакты, датчики разных плат меряют разные
комнаты, а доступность — это множество доступных плат, а не один флаг на весь дом.
Склеивание по номеру канала объявило бы чужое устройство и позволило бы
автоматике переключить реле на другой стороне дома.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState


@dataclass
class HomeState:
    """Всё, что известно о физическом слое одного дома.

    Attributes:
        user_id: Владелец дома.
        relay_states: Положение каждого канала каждой платы.
        readings: Последние показания датчиков каждой платы.
        last_reading_board: Плата, чьи показания пришли последними.
        online_boards: Платы, которые отвечают прямо сейчас.
        device_modes: Логический режим, приказанный каждому устройству.
        manual_override_until: Момент, до которого длится ручное управление.
        changed_at: Момент последнего изменения.
    """

    user_id: UserId
    relay_states: dict[EspDeviceId, dict[int, RelayState]] = field(default_factory=dict)
    readings: dict[EspDeviceId, ClimateReading] = field(default_factory=dict)
    last_reading_board: EspDeviceId | None = None
    online_boards: frozenset[EspDeviceId] = frozenset()
    device_modes: dict[DeviceId, DeviceStatus] = field(default_factory=dict)
    manual_override_until: datetime | None = None
    changed_at: datetime | None = None

    def is_relay_closed(self, board_id: EspDeviceId, channel: int) -> bool:
        """Сообщает, замкнут ли контакт реле этой платы.

        Args:
            board_id: Плата, чей канал спрашивают.
            channel: Номер канала реле.

        Returns:
            bool: True, когда контакт замкнут.
        """
        return self.relay_states.get(board_id, {}).get(channel) is RelayState.ON

    def apply_relay_report(
        self, board_id: EspDeviceId, states: Sequence[bool], changed_at: datetime
    ) -> tuple[int, ...]:
        """Принимает положения каналов, которые сообщила одна плата.

        Канал, о котором ещё ничего не известно, считается разомкнутым: плата,
        впервые назвавшая разомкнутый канал, ничего не изменила. Названное
        положение записывается всегда, поэтому прочитанное после записи совпадает с
        тем, что вернула запись.

        Args:
            board_id: Плата, чьи каналы пришли.
            states: Положения контактов по порядку каналов, начиная с первого.
            changed_at: Момент, когда плата их передала.

        Returns:
            tuple[int, ...]: Каналы этой платы, положение которых действительно
            изменилось.
        """
        stored = self.relay_states.setdefault(board_id, {})
        changed: list[int] = []
        for index, energized in enumerate(states, start=1):
            position = RelayState.ON if energized else RelayState.OFF
            if stored.get(index, RelayState.OFF) is not position:
                changed.append(index)
            stored[index] = position
        self.changed_at = changed_at
        return tuple(changed)

    def apply_command(
        self,
        board_id: EspDeviceId,
        device_id: DeviceId,
        channel: int,
        status: DeviceStatus,
        changed_at: datetime,
    ) -> None:
        """Записывает команду, которую плата подтвердила.

        Args:
            board_id: Плата, выполнившая команду.
            device_id: Затронутое устройство.
            channel: Канал реле этой платы.
            status: Состояние, в которое устройство привели.
            changed_at: Момент подтверждения.
        """
        channels = self.relay_states.setdefault(board_id, {})
        channels[channel] = RelayState.ON if status.is_active else RelayState.OFF
        self.device_modes[device_id] = status
        self.changed_at = changed_at

    def apply_reading(
        self, board_id: EspDeviceId, reading: ClimateReading, changed_at: datetime
    ) -> ClimateReading:
        """Принимает показания датчиков одной платы, сохраняя то, что они не измерили.

        Показания соседней платы при этом остаются нетронутыми: датчик каждой
        платы меряет свою комнату.

        Args:
            board_id: Плата, чьи датчики сообщили.
            reading: Измеренные значения; там, где датчик молчал, значения нет.
            changed_at: Момент сообщения.

        Returns:
            ClimateReading: Значения этой платы, которые действительно изменились.
        """
        previous = self.readings.get(board_id, ClimateReading())
        stored = ClimateReading(
            temperature=(
                previous.temperature if reading.temperature is None else reading.temperature
            ),
            humidity=previous.humidity if reading.humidity is None else reading.humidity,
        )
        self.readings[board_id] = stored
        self.last_reading_board = board_id
        self.changed_at = changed_at
        return ClimateReading(
            temperature=stored.temperature if stored.temperature != previous.temperature else None,
            humidity=stored.humidity if stored.humidity != previous.humidity else None,
        )

    @property
    def reading(self) -> ClimateReading:
        """Возвращает последние показания дома.

        Климат принадлежит плате: датчик каждой платы меряет свою комнату. Дому
        всё равно нужен один ответ, поэтому берутся показания платы, сообщившей
        последней: складывать комнаты в среднее значило бы выдумать измерение,
        которого никто не делал.

        Returns:
            ClimateReading: Последние показания или пустой снимок, когда их нет.
        """
        if self.last_reading_board is None:
            return ClimateReading()
        return self.readings.get(self.last_reading_board, ClimateReading())

    def set_board_available(
        self, board_id: EspDeviceId, online: bool, changed_at: datetime
    ) -> bool:
        """Записывает, доступна ли плата.

        Потеря платы не стирает приказанные режимы: пока плата молчит, её
        устройства и так недоступны, а стирать память соседней платы незачем.

        Args:
            board_id: Плата, о которой сообщили.
            online: True, когда плата ответила.
            changed_at: Момент перехода.

        Returns:
            bool: Доступность этой платы до перехода.
        """
        was_online = board_id in self.online_boards
        if online:
            self.online_boards = self.online_boards | {board_id}
        else:
            self.online_boards = self.online_boards - {board_id}
        self.changed_at = changed_at
        return was_online

    def is_board_online(self, board_id: EspDeviceId | None) -> bool:
        """Сообщает, отвечает ли плата.

        Args:
            board_id: Плата в вопросе или None для устройства, не закреплённого
                ни за одной платой.

        Returns:
            bool: True, когда плата в списке доступных.
        """
        return board_id is not None and board_id in self.online_boards

    @property
    def board_online(self) -> bool:
        """Сообщает, отвечает ли хоть одна плата дома."""
        return bool(self.online_boards)

    def status_of(self, device: Device) -> DeviceStatus:
        """Возвращает логическое состояние устройства сейчас.

        Args:
            device: Устройство, о котором спрашивают.

        Returns:
            DeviceStatus: Состояние, в котором устройство находится.
        """
        return self.status_for(device.id, int(device.channel), device.board_id)

    def status_for(
        self, device_id: DeviceId, channel: int, board_id: EspDeviceId | None
    ) -> DeviceStatus:
        """Возвращает логическое состояние по устройству, каналу и плате.

        Плата молчит — устройство недоступно; контакт разомкнут — выключено; иначе
        берут приказанный режим, а при его отсутствии считают, что устройство просто
        включено. Берётся канал именно той платы, на которой стоит устройство.

        Устройство, не закреплённое ни за одной платой, читается по единственной
        доступной плате дома — тем же правилом, по которому ему адресуется
        команда. При нескольких доступных платах такое устройство ни к чему не
        привязано и потому недоступно.

        Args:
            device_id: Идентификатор устройства.
            channel: Канал реле его платы.
            board_id: Плата, на которой оно стоит, или None, когда не закреплено.

        Returns:
            DeviceStatus: Состояние, в котором устройство находится.
        """
        if board_id is None:
            if len(self.online_boards) != 1:
                return DeviceStatus.UNAVAILABLE
            board_id = next(iter(self.online_boards))
        if not self.is_board_online(board_id):
            return DeviceStatus.UNAVAILABLE
        if not self.is_relay_closed(board_id, channel):
            return DeviceStatus.OFF
        return self.device_modes.get(device_id, DeviceStatus.ACTIVE)

    def forget_device(self, device_id: DeviceId) -> None:
        """Забывает всё, что помнилось об исчезнувшем устройстве.

        Args:
            device_id: Идентификатор удалённого устройства.
        """
        self.device_modes.pop(device_id, None)

    def suspend_automation_until(self, moment: datetime) -> None:
        """Держит автоматику в стороне до указанного момента.

        Args:
            moment: Момент, до которого длится ручное управление.
        """
        self.manual_override_until = moment

    def resume_automation(self) -> None:
        """Закрывает окно ручного управления немедленно."""
        self.manual_override_until = None

    def is_automation_suspended(self, now: datetime) -> bool:
        """Сообщает, удерживает ли сейчас автоматику ручное управление.

        Args:
            now: Момент, относительно которого решают.

        Returns:
            bool: True внутри окна ручного управления.
        """
        return self.manual_override_until is not None and now < self.manual_override_until

    def suspend_automation_for(self, now: datetime, minutes: int) -> None:
        """Удерживает автоматику в стороне на несколько минут.

        Args:
            now: Момент, когда человек вмешался.
            minutes: Длину окна.
        """
        self.manual_override_until = now + timedelta(minutes=max(0, minutes))
