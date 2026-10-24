"""Шина команд платам между процессами через асинхронный Redis Pub/Sub.

WebSocket-сервер плат живёт в одном процессе и является единственным владельцом
соединений. Всякий другой процесс, которому нужно тронуть железо — рабочий с
автоматикой и сценариями, — не имеет права поднимать второй сервер плат: он публикует
команду в канал аккаунта, а сервер плат её читает, исполняет на настоящем соединении и
возвращает ответ в канал самой команды. Отправка и ожидание ответа объединены в один
шаг, чтобы подписка открылась раньше, чем публикация успела породить ответ, — иначе
короткая команда могла бы остаться непрочитанной.

Очередь сообщений ведёт ``redis.asyncio`` без единого потока: подписка и чтение
неблокирующие, поэтому цикл событий одного процесса не утаскивает за собой второй.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID

from redis.asyncio import Redis as AsyncRedis

from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.brokers import keys

SET_RELAY: Final = "set_relay"
SET_NETWORK: Final = "set_network"
REQUEST_STATE: Final = "request_state"

NO_REASON: Final = None


@dataclass(frozen=True, slots=True)
class BoardCommand:
    """Одна команда плате, передаваемая между процессами.

    Attributes:
        command_id: Идентификатор, по которому команда найдёт свой ответ.
        user_id: Владелец платы.
        board_id: Идентификатор платы.
        kind: Род команды — переключение, сеть или запрос состояния.
        channel: Физический канал реле для переключения.
        energized: Замкнуть ли контакт для переключения.
        network: Сеть для смены настроек, собранная из полей профиля.
    """

    command_id: str
    user_id: UserId
    board_id: EspDeviceId
    kind: str
    channel: int | None = None
    energized: bool | None = None
    network: dict[str, Any] | None = None

    def to_json(self) -> str:
        """Сериализует команду в кадр для канала.

        Returns:
            str: JSON команды.
        """
        return json.dumps(
            {
                "command_id": self.command_id,
                "user_id": str(self.user_id),
                "board_id": str(self.board_id),
                "kind": self.kind,
                "channel": self.channel,
                "energized": self.energized,
                "network": self.network,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str) -> BoardCommand | None:
        """Разбирает кадр канала в команду либо возвращает None для мусора.

        Args:
            raw: Текст, прочитанный из канала.

        Returns:
            BoardCommand | None: Разобранная команда или None, когда кадр не годится.
        """
        try:
            decoded = json.loads(raw)
        except ValueError:
            return None
        if not isinstance(decoded, dict):
            return None
        command_id = decoded.get("command_id")
        user_id = decoded.get("user_id")
        board_id = decoded.get("board_id")
        kind = decoded.get("kind")
        if not isinstance(command_id, str) or not isinstance(kind, str):
            return None
        if not isinstance(user_id, (str, UUID)) or not isinstance(board_id, (str, UUID)):
            return None
        try:
            network = decoded.get("network")
            return cls(
                command_id=command_id,
                user_id=UserId.parse(user_id),
                board_id=EspDeviceId.parse(board_id),
                kind=kind,
                channel=_as_int(decoded.get("channel")),
                energized=_as_bool(decoded.get("energized")),
                network=network if isinstance(network, dict) else None,
            )
        except Exception:
            return None

    def network_profile(self) -> NetworkProfile | None:
        """Восстанавливает профиль сети из сериализованных полей.

        Returns:
            NetworkProfile | None: Профиль либо None, когда его нет или он неполон.
        """
        if self.network is None:
            return None
        try:
            return NetworkProfile(
                ssid=str(self.network["ssid"]),
                password=str(self.network["password"]),
                host=str(self.network["host"]),
                server_port=int(self.network["server_port"]),
                socket_port=int(self.network["socket_port"]),
                socket_path=str(self.network["socket_path"]),
            )
        except (KeyError, ValueError, TypeError):
            return None

    @staticmethod
    def network_of(profile: NetworkProfile) -> dict[str, Any]:
        """Превращает профиль сети в переносимый словарь.

        Args:
            profile: Профиль сети платы.

        Returns:
            dict[str, Any]: Поля профиля, сериализуемые в JSON.
        """
        return {
            "ssid": profile.ssid,
            "password": profile.password,
            "host": profile.host,
            "server_port": profile.server_port,
            "socket_port": profile.socket_port,
            "socket_path": profile.socket_path,
        }


class RedisBoardCommandBus:
    """Публикация команд платам и приём ответов поверх Redis Pub/Sub.

    Args:
        redis: Асинхронное соединение с Redis.
        key_prefix: Пространство имён каналов.
        result_timeout_sec: Сколько секунд команда ждёт ответ сервера плат.
    """

    def __init__(self, redis: AsyncRedis, key_prefix: str, result_timeout_sec: float) -> None:
        """Инициализирует шину.

        Args:
            redis: Асинхронное соединение с Redis.
            key_prefix: Пространство имён каналов.
            result_timeout_sec: Сколько секунд команда ждёт ответ сервера плат.
        """
        self._redis = redis
        self._prefix = key_prefix
        self._timeout_sec = result_timeout_sec

    async def execute(self, command: BoardCommand) -> tuple[bool, str | None]:
        """Публикует команду и дожидается её ответа.

        Подписка на канал ответа открывается до публикации, поэтому быстрый ответ не
        теряется, а таймаут превращает молчание сервера плат в явный отказ доставки.

        Args:
            command: Команда, которую надо исполнить на настоящем соединении.

        Returns:
            tuple[bool, str | None]: Приняла ли плата команду и почему нет, если нет.
        """
        channel = keys.board_result_channel(self._prefix, command.command_id)
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(channel)
        try:
            await self._redis.publish(
                keys.board_command_channel(self._prefix, command.user_id), command.to_json()
            )
            return await self._read_result(pubsub)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def notify(self, command: BoardCommand) -> None:
        """Публикует команду без ожидания ответа — для запроса состояния.

        Args:
            command: Команда, ответ на которую не нужен.
        """
        await self._redis.publish(
            keys.board_command_channel(self._prefix, command.user_id), command.to_json()
        )

    async def publish_result(self, command_id: str, accepted: bool, reason: str | None) -> None:
        """Публикует ответ исполненной команды в её канал.

        Args:
            command_id: Идентификатор команды, чей ответ уходит.
            accepted: Приняла ли команда плата.
            reason: Причина отказа, если команда не прошла.
        """
        payload = json.dumps(
            {"accepted": accepted, "reason": reason},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        await self._redis.publish(keys.board_result_channel(self._prefix, command_id), payload)

    def commands(self) -> AsyncIterator[BoardCommand]:
        """Отдаёт всякую команду, адресованную платам любого аккаунта.

        Returns:
            AsyncIterator[BoardCommand]: Поток разобранных команд по мере прихода.
        """

        async def stream() -> AsyncIterator[BoardCommand]:
            pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
            await pubsub.psubscribe(keys.board_command_pattern(self._prefix))
            try:
                while True:
                    message = await pubsub.get_message(timeout=1.0)
                    if message is None:
                        continue
                    data = message.get("data")
                    if not isinstance(data, (str, bytes, bytearray)):
                        continue
                    command = BoardCommand.from_json(_as_text(data))
                    if command is not None:
                        yield command
            finally:
                await pubsub.punsubscribe(keys.board_command_pattern(self._prefix))
                await pubsub.aclose()

        return stream()

    async def _read_result(self, pubsub: Any) -> tuple[bool, str | None]:
        """Ждёт первый ответ в канале команды в пределах таймаута."""
        try:
            async with asyncio.timeout(self._timeout_sec):
                while True:
                    message = await pubsub.get_message(timeout=self._timeout_sec)
                    if message is None:
                        continue
                    payload = _decode_result(message.get("data"))
                    return payload[0], payload[1]
        except TimeoutError:
            return False, "ack_timeout"


def _decode_result(data: Any) -> tuple[bool, str | None]:
    """Разбирает кадр ответа на пару «принято — причина»."""
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8", "replace")
    if not isinstance(data, str):
        return False, "esp_delivery_failed"
    try:
        decoded = json.loads(data)
    except ValueError:
        return False, "esp_delivery_failed"
    if not isinstance(decoded, dict):
        return False, "esp_delivery_failed"
    return bool(decoded.get("accepted")), decoded.get("reason")


def _as_text(data: str | bytes | bytearray) -> str:
    """Приводит сырое значение канала к тексту."""
    if isinstance(data, (bytes, bytearray)):
        return data.decode("utf-8", "replace")
    return data


def _as_int(value: Any) -> int | None:
    """Возвращает целое из значения канала либо None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    """Возвращает логическое из значения канала либо None."""
    if value is None:
        return None
    return bool(value)
