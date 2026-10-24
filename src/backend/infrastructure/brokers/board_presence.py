"""Присутствие подключённых плат в Redis: единственный реестр для всех процессов.

Раньше реестр жил словарём в памяти того процесса, что держит WebSocket-сервер плат.
Из-за этого рабочий, выполняющий автоматику и сценарии, не видел ни одной платы и
команды железа физически не могли до неё дойти. Перенос реестра в Redis с TTL делает
его видимым любому процессу: сервер плат отмечает приход и уход, а рабочий читает это,
не имея собственного соединения с платами.

Ключ живёт ровно столько, сколько плата может молчать, и продлевается при каждом её
сообщении: уроненный процесс сервера перестаёт продлевать ключ, и плата исчезает из
реестра сама, без явного снятия.
"""

from __future__ import annotations

from redis.asyncio import Redis as AsyncRedis

from backend.application.interfaces.services.boards.board_availability import BoardAvailability
from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.brokers import keys
from backend.infrastructure.brokers.decoding import as_text


class RedisBoardPresence(BoardAvailability):
    """Реестр подключённых плат, разделённый между процессами через Redis.

    Args:
        redis: Асинхронное соединение, в котором живут ключи присутствия.
        key_prefix: Пространство имён, с которого начинается каждый ключ.
        ttl_sec: Сколько секунд плата считается присутствующей без продления.
    """

    def __init__(self, redis: AsyncRedis, key_prefix: str, ttl_sec: float) -> None:
        """Инициализирует реестр.

        Args:
            redis: Асинхронное соединение, в котором живут ключи присутствия.
            key_prefix: Пространство имён, с которого начинается каждый ключ.
            ttl_sec: Сколько секунд плата считается присутствующей без продления.
        """
        self._redis = redis
        self._prefix = key_prefix
        self._ttl_sec = ttl_sec

    async def mark_online(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Сообщает, что плата подключена, и задаёт срок её присутствия.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
        """
        await self._redis.set(
            keys.board_presence_key(self._prefix, user_id, board_id), "1", ex=self._ttl()
        )

    async def refresh(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Продлевает присутствие платы на весь срок.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
        """
        await self._redis.set(
            keys.board_presence_key(self._prefix, user_id, board_id), "1", ex=self._ttl()
        )

    async def mark_offline(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Сообщает, что плата отключилась, и убирает её из реестра.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
        """
        await self._redis.delete(keys.board_presence_key(self._prefix, user_id, board_id))

    async def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Возвращает True, когда плата сейчас присутствует в реестре.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Returns:
            bool: True, когда ключ присутствия жив.
        """
        found = await self._redis.exists(keys.board_presence_key(self._prefix, user_id, board_id))
        return bool(found)

    async def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Возвращает единственную подключённую плату аккаунта.

        Логическое устройство пока не хранит идентификатор платы, поэтому команда
        адресуется лишь тогда, когда у аккаунта ровно одна подключённая плата: при
        двух угадать целевую нельзя, при нулевой обращаться не к кому.

        Args:
            user_id: Владелец плат.

        Returns:
            EspDeviceId | None: Идентификатор платы или None, когда плат не ровно одна.
        """
        boards = [
            EspDeviceId.parse(self._board_of(name))
            async for raw in self._redis.scan_iter(
                match=keys.board_presence_pattern(self._prefix, user_id), count=100
            )
            if (name := as_text(raw)) is not None
        ]
        if len(boards) != 1:
            return None
        return boards[0]

    async def online_user_ids(self) -> list[UserId]:
        """Возвращает аккаунты, у которых сейчас есть подключённая плата.

        Рабочему это нужно, чтобы не сканировать всю базу ради автоматики: без
        подключённой платы автоматизировать нечего, а множество присутствия уже живёт в
        Redis и обновляется сервером плат.

        Returns:
            list[UserId]: Различные владельцы хотя бы одной подключённой платы.
        """
        pattern = keys.board_presence_all_pattern(self._prefix)
        owners: set[UserId] = set()
        async for raw in self._redis.scan_iter(match=pattern, count=100):
            name = as_text(raw)
            if name is not None:
                owners.add(UserId.parse(self._user_of(name)))
        return sorted(owners, key=str)

    async def is_any_online(self, user_id: UserId) -> bool:
        """Возвращает True, когда у аккаунта есть хотя бы одна подключённая плата.

        Реестр присутствия — единственный источник истины о том, в сети ли плата: ключ
        живёт несколько секунд и продлевается каждым её сообщением, поэтому ответ всегда
        свежий, а не защёлкнутый когда-то флаг.

        Args:
            user_id: Владелец плат.

        Returns:
            bool: True при наличии хотя бы одного живого ключа присутствия.
        """
        pattern = keys.board_presence_pattern(self._prefix, user_id)
        async for _ in self._redis.scan_iter(match=pattern, count=1):
            return True
        return False

    def _user_of(self, name: str) -> str:
        """Вырезает идентификатор владельца из ключа присутствия."""
        return name.split(":")[-2]

    def _board_of(self, name: str) -> str:
        """Вырезает идентификатор платы из хвоста ключа присутствия."""
        return name.rsplit(":", 1)[-1]

    def _ttl(self) -> int:
        """Возвращает срок присутствия целым числом секунд, каким его требует Redis."""
        return max(1, round(self._ttl_sec))
