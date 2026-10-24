"""Шина команд платам между процессами через асинхронный Redis Pub/Sub.

WebSocket-сервер плат живёт в одном процессе и является единственным владельцом
соединений. Всякий другой процесс, которому нужно тронуть железо — рабочий с
автоматикой и сценариями, — не имеет права поднимать второй сервер плат: он публикует
команду в канал аккаунта, а сервер плат её читает, исполняет на настоящем соединении и
возвращает ответ в канал самой команды. Отправка и ожидание ответа объединены в один
шаг, чтобы подписка открылась раньше, чем публикация успела породить ответ, — иначе
короткая команда могла бы остаться непрочитанной.

Канал общий на аккаунт, а не на команду, поэтому секреты в кадр не попадают: пароль
сети отправитель оставляет в короткоживущем ключе и называет его идентификатором
команды, а исполнитель забирает секрет оттуда одноразово и сразу его удаляет.

Очередь сообщений ведёт ``redis.asyncio`` без единого потока: подписка и чтение
неблокирующие, поэтому цикл событий одного процесса не утаскивает за собой второй.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Final
from uuid import UUID

from redis.asyncio import Redis as AsyncRedis

from backend.application.dto.boards.board_command_reason import BoardCommandReason
from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.domain.exceptions import MalformedIdentifierError
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.brokers import keys
from backend.infrastructure.system.logging import get_logger

log = get_logger("board.command_bus")

SET_RELAY: Final = "set_relay"
SET_NETWORK: Final = "set_network"
REQUEST_STATE: Final = "request_state"

SECRET_TTL_SEC: Final = 60


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
        network: Сеть для смены настроек без пароля, собранная из полей профиля.
        secret: Пароль сети, живущий только в памяти отправителя и в отдельном
            ключе хранилища: в кадр он не сериализуется и в журнал не попадает.
    """

    command_id: str
    user_id: UserId
    board_id: EspDeviceId
    kind: str
    channel: int | None = None
    energized: bool | None = None
    network: dict[str, Any] | None = None
    secret: str | None = field(default=None, repr=False)

    def to_json(self) -> str:
        """Сериализует команду в кадр для канала.

        Returns:
            str: JSON команды без секрета: он ходит отдельным ключом.
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
            log.warning("board.command_unreadable", frame=raw[:120])
            return None
        if not isinstance(decoded, dict):
            log.warning("board.command_unreadable", frame=raw[:120])
            return None
        command_id = decoded.get("command_id")
        user_id = decoded.get("user_id")
        board_id = decoded.get("board_id")
        kind = decoded.get("kind")
        if not isinstance(command_id, str) or not isinstance(kind, str):
            log.warning("board.command_incomplete", frame=raw[:120])
            return None
        if not isinstance(user_id, (str, UUID)) or not isinstance(board_id, (str, UUID)):
            log.warning("board.command_incomplete", frame=raw[:120])
            return None
        try:
            owner = UserId.parse(user_id)
            board = EspDeviceId.parse(board_id)
        except MalformedIdentifierError:
            log.warning("board.command_bad_identity", frame=raw[:120])
            return None
        network = decoded.get("network")
        return cls(
            command_id=command_id,
            user_id=owner,
            board_id=board,
            kind=kind,
            channel=_as_int(decoded.get("channel")),
            energized=_as_bool(decoded.get("energized")),
            network=network if isinstance(network, dict) else None,
        )

    def network_profile(self, password: str | None) -> NetworkProfile | None:
        """Восстанавливает профиль сети, подставляя секрет, взятый из хранилища.

        Args:
            password: Пароль сети, забранный исполнителем из короткоживущего ключа.

        Returns:
            NetworkProfile | None: Профиль либо None, когда он неполон.
        """
        if self.network is None or password is None:
            return None
        try:
            return NetworkProfile(
                ssid=str(self.network["ssid"]),
                password=password,
                host=str(self.network["host"]),
                server_port=int(self.network["server_port"]),
                socket_port=int(self.network["socket_port"]),
                socket_path=str(self.network["socket_path"]),
            )
        except (KeyError, ValueError, TypeError):
            return None

    @staticmethod
    def network_of(profile: NetworkProfile) -> dict[str, Any]:
        """Превращает профиль сети в переносимый словарь без пароля.

        Args:
            profile: Профиль сети платы.

        Returns:
            dict[str, Any]: Поля профиля, сериализуемые в JSON без секрета.
        """
        return {
            "ssid": profile.ssid,
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

    async def execute(self, command: BoardCommand) -> BoardCommandResult:
        """Публикует команду и дожидается её ответа.

        Подписка на канал ответа открывается до публикации, поэтому быстрый ответ не
        теряется, а таймаут превращает молчание сервера плат в явный отказ доставки.

        Args:
            command: Команда, которую надо исполнить на настоящем соединении.

        Returns:
            BoardCommandResult: Ответ платы — подтверждение или причина отказа.
        """
        channel = keys.board_result_channel(self._prefix, command.command_id)
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(channel)
        try:
            await self._publish(command)
            return await self._read_result(pubsub)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def notify(self, command: BoardCommand) -> None:
        """Публикует команду без ожидания ответа — для запроса состояния.

        Args:
            command: Команда, ответ на которую не нужен.
        """
        await self._publish(command)

    async def take_secret(self, command_id: str) -> str | None:
        """Забирает и удаляет секрет одной команды.

        Чтение с удалением делает ключ одноразовым: второй исполнитель той же команды
        получит None и ответит отказом, а не повторит смену сети с тем же паролем.

        Args:
            command_id: Идентификатор команды, чей секрет нужен.

        Returns:
            str | None: Секрет либо None, когда его уже нет или ключ истёк.
        """
        value = await self._redis.getdel(keys.board_secret_key(self._prefix, command_id))
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", "replace")
        return value

    async def _publish(self, command: BoardCommand) -> None:
        """Кладёт секрет в короткоживущий ключ и публикует кадр без него.

        Args:
            command: Команда, которая уходит плате.
        """
        if command.secret is not None:
            await self._redis.set(
                keys.board_secret_key(self._prefix, command.command_id),
                command.secret,
                px=SECRET_TTL_SEC * 1000,
            )
        await self._redis.publish(
            keys.board_command_channel(self._prefix, command.user_id), command.to_json()
        )

    async def publish_result(self, command_id: str, result: BoardCommandResult) -> None:
        """Публикует ответ исполненной команды в её канал.

        Args:
            command_id: Идентификатор команды, чей ответ уходит.
            result: Итог исполнения — принято ли командой платой и почему нет.
        """
        payload = json.dumps(
            {"accepted": result.accepted, "reason": result.reason},
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
            pattern = keys.board_command_pattern(self._prefix)
            pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
            await pubsub.psubscribe(pattern)
            try:
                async for message in pubsub.listen():
                    data = message.get("data")
                    if not isinstance(data, (str, bytes, bytearray)):
                        continue
                    command = BoardCommand.from_json(_as_text(data))
                    if command is not None:
                        yield command
            finally:
                await pubsub.punsubscribe(pattern)
                await pubsub.aclose()

        return stream()

    async def _read_result(self, pubsub: Any) -> BoardCommandResult:
        """Ждёт первый ответ в канале команды в пределах таймаута.

        Returns:
            BoardCommandResult: Ответ платы либо отказ по таймауту или доставке.
        """
        try:
            async with asyncio.timeout(self._timeout_sec):
                messages = pubsub.listen()
                try:
                    async for message in messages:
                        return _decode_result(message.get("data"))
                finally:
                    await messages.aclose()
        except TimeoutError:
            return BoardCommandResult(accepted=False, reason=BoardCommandReason.ACK_TIMEOUT)
        return BoardCommandResult(accepted=False, reason=BoardCommandReason.DELIVERY_FAILED)


def _decode_result(data: Any) -> BoardCommandResult:
    """Разбирает кадр ответа в типизированный итог команды.

    Args:
        data: Значение, прочитанное из канала ответа.

    Returns:
        BoardCommandResult: Ответ платы либо отказ доставки для мусорного кадра.
    """
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8", "replace")
    if not isinstance(data, str):
        return BoardCommandResult(accepted=False, reason=BoardCommandReason.DELIVERY_FAILED)
    try:
        decoded = json.loads(data)
    except ValueError:
        return BoardCommandResult(accepted=False, reason=BoardCommandReason.DELIVERY_FAILED)
    if not isinstance(decoded, dict):
        return BoardCommandResult(accepted=False, reason=BoardCommandReason.DELIVERY_FAILED)
    return BoardCommandResult(accepted=bool(decoded.get("accepted")), reason=decoded.get("reason"))


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
