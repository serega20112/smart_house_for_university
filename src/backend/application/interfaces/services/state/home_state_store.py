"""Хранилище изменчивого состояния дома.

Состояние переживает процесс: перезапуск не должен объявлять все платы потерянными,
а несколько рабочих должны договариваться о том, что делают реле. Каждая операция —
утверждение о домене, применяемое на сервере атомарно, поэтому два писателя не
стирают факт друг друга: ни одна операция не читает всё состояние, не правит объект
и не пишет его целиком обратно.

Всё физическое здесь ключуется платой: у каждой платы свои каналы, свой датчик и
своя доступность. Без платы в подписи операция над домом из двух плат была бы
двусмысленной — какой канал 1 имеется в виду.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus


class HomeStateStore(ABC):
    """Надёжное хранилище изменчивого состояния физического уровня."""

    @abstractmethod
    async def read(self, user_id: UserId) -> HomeState:
        """Последнее известное состояние дома."""

    @abstractmethod
    async def record_background_reading(
        self, user_id: UserId, board_id: EspDeviceId, reading: ClimateReading, changed_at: datetime
    ) -> ClimateReading:
        """Применяет показания датчиков, сообщённые одной платой."""

    @abstractmethod
    async def record_relay_report(
        self, user_id: UserId, board_id: EspDeviceId, states: Sequence[bool], changed_at: datetime
    ) -> tuple[int, ...]:
        """Применяет положения реле платы и возвращает сдвинувшиеся каналы."""

    @abstractmethod
    async def record_board_online(
        self, user_id: UserId, board_id: EspDeviceId, online: bool, changed_at: datetime
    ) -> bool:
        """Записывает доступность платы, возвращая её прежнее значение.

        Прежнее значение нужно, чтобы вызывающий понял, сдвинулось ли состояние
        дома вообще.
        """

    @abstractmethod
    async def record_command_result(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        device_id: DeviceId,
        channel: int,
        status: DeviceStatus,
        changed_at: datetime,
    ) -> None:
        """Сохраняет подтверждённый платой результат команды."""

    @abstractmethod
    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        """Забывает всё об устройстве, которого больше нет."""

    @abstractmethod
    async def set_override_until(self, user_id: UserId, until: datetime | None) -> None:
        """Устанавливает или снимает окно ручного приоритета.

        Окно — один ключ с нативным сроком жизни, поэтому никому не нужно
        вычитать минуты из сохранённой отметки, чтобы понять, что окно закрылось.
        """

    @abstractmethod
    async def claim_summary_slot(self, user_id: UserId, key: str, window_sec: int) -> bool:
        """Забирает право отправить редкое уведомление."""
