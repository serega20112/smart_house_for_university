"""Адаптер хранилища живого состояния дома к порту прикладного слоя.

Состояние дома переживает процесс: перезапуск не должен делать все платы
недоступными, а несколько воркеров должны сойтись на том, что делают контакты.
Поэтому состояние живёт в Redis, а не в словаре запущенного процесса.

Здесь только порядок вызовов: что прочитать и каким скриптом применить. Как это
лежит в хешах и скриптах — :mod:`state_schema`, как называются ключи —
:mod:`keys`.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Sequence
from datetime import datetime
from typing import Any

from redis.asyncio import Redis

from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.domain.aggregates.device.device import Device
from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState
from backend.infrastructure.brokers import keys
from backend.infrastructure.brokers.decoding import as_text
from backend.infrastructure.brokers.state_schema import (
    APPLY_RELAYS,
    APPLY_SENSOR_REPORT,
    FORGET_DEVICE_STATUS,
    RECORD_BOARD_REACHABILITY,
    RECORD_COMMAND_RESULT,
    VALUE_FALSE,
    VALUE_TRUE,
    home_state_of,
)


class RedisHomeStateStore(HomeStateStore):
    """Читает и пишет состояние дома одним хешем Redis.

    Args:
        redis: Соединение, в котором живёт состояние.
        key_prefix: Пространство имён всех ключей этого адаптера.
    """

    def __init__(self, redis: Redis, key_prefix: str) -> None:
        """Инициализирует хранилище.

        Args:
            redis: Соединение, в котором живёт состояние.
            key_prefix: Пространство имён всех ключей этого адаптера.
        """
        self._redis = redis
        self._prefix = key_prefix

    async def read(self, user_id: UserId) -> HomeState:
        """Возвращает последнее известное состояние дома.

        Args:
            user_id: Владелец дома.

        Returns:
            HomeState: Сохранённое состояние, пустое там, где ничего не сообщали.
        """
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hgetall(keys.state_key(self._prefix, user_id))
            pipe.get(keys.override_key(self._prefix, user_id))
            stored, override = await pipe.execute()
        return home_state_of(user_id, stored, as_text(override))

    async def record_background_reading(
        self, user_id: UserId, reading: ClimateReading, changed_at: datetime
    ) -> ClimateReading:
        """Применяет показания датчиков, сообщённые платой.

        Args:
            user_id: Владелец дома.
            reading: Измеренные значения, отсутствующие там, где датчик молчал.
            changed_at: Момент, когда плата их измерила.

        Returns:
            ClimateReading: Те значения, которые действительно сдвинулись.
        """
        moves = json.loads(
            await self._eval(
                APPLY_SENSOR_REPORT,
                user_id,
                repr(reading.temperature.celsius) if reading.temperature is not None else "",
                repr(reading.humidity.percent) if reading.humidity is not None else "",
                changed_at.isoformat(),
            )
        )
        if not isinstance(moves, dict):
            moves = {}
        return ClimateReading.measured(
            float(moves["temperature"]) if "temperature" in moves else None,
            float(moves["humidity"]) if "humidity" in moves else None,
        )

    async def record_relay_report(
        self, user_id: UserId, states: Sequence[bool], changed_at: datetime
    ) -> tuple[int, ...]:
        """Применяет положения контактов, о которых сообщила плата.

        Args:
            user_id: Владелец платы.
            states: Положения контактов по порядку каналов, начиная с первого.
            changed_at: Момент сообщения.

        Returns:
            tuple[int, ...]: Каналы, положение которых действительно изменилось.
        """
        moved: list[int] = json.loads(
            await self._eval(
                APPLY_RELAYS,
                user_id,
                json.dumps([bool(state) for state in states]),
                changed_at.isoformat(),
            )
        )
        return tuple(moved)

    async def record_board_online(
        self, user_id: UserId, online: bool, changed_at: datetime
    ) -> bool:
        """Запоминает, доступна ли плата.

        Args:
            user_id: Владелец платы.
            online: True, когда плата ответила, False, когда пропала.
            changed_at: Момент перехода.

        Returns:
            bool: Доступность такой, какой она была до перехода.
        """
        previous = await self._eval(
            RECORD_BOARD_REACHABILITY,
            user_id,
            VALUE_TRUE if online else VALUE_FALSE,
            changed_at.isoformat(),
        )
        return as_text(previous) == VALUE_TRUE

    async def record_command_result(
        self,
        user_id: UserId,
        device: Device,
        status: DeviceStatus,
        changed_at: datetime,
    ) -> None:
        """Сохраняет результат команды, подтверждённый платой.

        Args:
            user_id: Владелец устройства.
            device: Устройство, над которым прошла команда.
            status: Состояние, в которое устройство перевели.
            changed_at: Момент подтверждения.
        """
        if device.channel is None:
            return
        await self._eval(
            RECORD_COMMAND_RESULT,
            user_id,
            str(int(device.channel)),
            RelayState.ON.value if status.is_active else RelayState.OFF.value,
            str(device.id),
            status.value,
            changed_at.isoformat(),
        )

    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        """Забывает всё, что помнилось об исчезнувшем устройстве.

        Args:
            user_id: Владелец удалённого устройства.
            device_id: Идентификатор удалённого устройства.
        """
        await self._eval(FORGET_DEVICE_STATUS, user_id, str(device_id))

    async def set_override_until(self, user_id: UserId, until: datetime | None) -> None:
        """Открывает или закрывает окно ручного управления домом.

        Окно — один ключ с собственным сроком жизни, поэтому никому не пришлось
        вычитать минуты из сохранённой метки времени, чтобы узнать, кончился ли
        срок.

        Args:
            user_id: Владелец дома.
            until: Момент закрытия окна или None, чтобы закрыть сейчас.
        """
        key = keys.override_key(self._prefix, user_id)
        if until is None:
            await self._redis.delete(key)
            return
        await self._redis.set(key, until.isoformat())
        await self._redis.pexpireat(key, int(until.timestamp() * 1000))

    async def claim_summary_slot(self, user_id: UserId, key: str, window_sec: int) -> bool:
        """Занимает право отправить одно периодическое уведомление.

        Решение принимает хранилище: именно это мешает двум воркерам сообщить об
        одном и том же прогрессе сценария в один момент.

        Args:
            user_id: Владелец дома.
            key: Название ограничиваемого потока сообщений.
            window_sec: Длина окна в секундах.

        Returns:
            bool: True, когда окно занял этот вызов и слать можно.
        """
        name = keys.throttle_key(self._prefix, user_id, key)
        return bool(await self._redis.set(name, VALUE_TRUE, ex=max(1, window_sec), nx=True))

    async def _eval(self, lua: str, user_id: UserId, *args: str) -> Any:
        """Запускает скрипт на хеше состояния одного дома.

        Args:
            lua: Исходник скрипта.
            user_id: Владелец дома, чей хеш обрабатывается.
            args: Аргументы скрипта, все уже как текст.

        Returns:
            Any: Ответ сервера таким, каким его вернул протокол.
        """
        answer: Awaitable[Any] | str = self._redis.eval(
            lua, 1, keys.state_key(self._prefix, user_id), *args
        )
        if isinstance(answer, str):
            return answer
        return await answer
