"""
Живое состояние одного дома, снятое с его платы.

Это состояние аккаунта, а не самостоятельный корень: дочерних сущностей у него
нет — положения каналов, приказанные режимы и окно ручного управления.
Состояние детерминировано: часы он не читает, момент приносит вызывающий.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState


@dataclass
class HomeState:
    """Всё, что известно о физическом слое одного дома.

    Attributes:
        user_id: Владелец дома.
        relay_states: Положение каждого канала реле.
        reading: Последние измерения датчиков климата.
        board_online: Доступна ли плата.
        device_modes: Логический режим, приказанный каждому устройству.
        manual_override_until: Момент, до которого длится ручное управление.
        changed_at: Момент последнего изменения.
    """

    user_id: UserId
    relay_states: dict[int, RelayState] = field(default_factory=dict)
    reading: ClimateReading = field(default_factory=ClimateReading)
    board_online: bool = False
    device_modes: dict[DeviceId, DeviceStatus] = field(default_factory=dict)
    manual_override_until: datetime | None = None
    changed_at: datetime | None = None

    def is_relay_closed(self, channel: int) -> bool:
        """Сообщает, замкнут ли контакт реле.

        Args:
            channel: Номер канала реле.

        Returns:
            bool: True, когда контакт замкнут.
        """
        return self.relay_states.get(channel) is RelayState.ON

    def apply_relay_report(self, states: list[bool], changed_at: datetime) -> tuple[int, ...]:
        """Принимает положения каналов, которые сообщило железо.

        Args:
            states: Положения контактов по порядку каналов, начиная с первого.
            changed_at: Момент, когда плата их передала.

        Returns:
            tuple[int, ...]: Каналы, положение которых действительно изменилось.
        """
        changed: list[int] = []
        for index, energized in enumerate(states, start=1):
            if self.is_relay_closed(index) is bool(energized):
                continue
            self.relay_states[index] = RelayState.ON if energized else RelayState.OFF
            changed.append(index)
        self.changed_at = changed_at
        return tuple(changed)

    def apply_command(self, device: Device, status: DeviceStatus, changed_at: datetime) -> None:
        """Записывает команду, которую плата подтвердила.

        Args:
            device: Затронутое устройство.
            status: Состояние, в которое устройство привели.
            changed_at: Момент подтверждения.
        """
        self.relay_states[int(device.channel)] = (
            RelayState.ON if status.is_active else RelayState.OFF
        )
        self.device_modes[device.id] = status
        self.changed_at = changed_at

    def apply_reading(self, reading: ClimateReading, changed_at: datetime) -> ClimateReading:
        """Принимает показания датчиков, сохраняя то, что они не измерили.

        Args:
            reading: Измеренные значения; там, где датчик молчал, значения нет.
            changed_at: Момент сообщения.

        Returns:
            ClimateReading: Значения, которые действительно изменились.
        """
        previous = self.reading
        self.reading = ClimateReading(
            temperature=(
                previous.temperature if reading.temperature is None else reading.temperature
            ),
            humidity=previous.humidity if reading.humidity is None else reading.humidity,
        )
        self.changed_at = changed_at
        return ClimateReading(
            temperature=(
                self.reading.temperature
                if self.reading.temperature != previous.temperature
                else None
            ),
            humidity=(
                self.reading.humidity if self.reading.humidity != previous.humidity else None
            ),
        )

    def set_board_available(self, online: bool, changed_at: datetime) -> None:
        """Записывает, доступна ли плата.

        Args:
            online: True, когда плата ответила.
            changed_at: Момент перехода.
        """
        self.board_online = online
        if not online:
            self.device_modes.clear()
        self.changed_at = changed_at

    def status_of(self, device: Device) -> DeviceStatus:
        """Возвращает логическое состояние устройства сейчас."""
        return self.status_for(device.id, int(device.channel))

    def status_for(self, device_id: DeviceId, channel: int) -> DeviceStatus:
        """Возвращает логическое состояние по его идентификатору и каналу.

        Плата молчит -- устройство недоступно; контакт разомкнут -- выключено; иначе
        берут приказанный режим, а при его отсутствии считают, что устройство просто
        включено.

        Args:
            device_id: Идентификатор устройства.
            channel: Канал реле, к которому устройство подключено.

        Returns:
            DeviceStatus: Состояние, в котором устройство находится.
        """
        if not self.board_online:
            return DeviceStatus.UNAVAILABLE
        if not self.is_relay_closed(channel):
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
