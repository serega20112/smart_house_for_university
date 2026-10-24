"""WebSocket-транспорт между бэкендом и платами.

Бэкенд слушает, а каждая плата дозванивается сама как клиент: плата в любой
домашней сети достигает сервера в интернете, не требуя входящих соединений.

Здесь ровно то, что умеет транспорт: сервер, дверь для чужого пути, чтение и запись
текстовых рамок, сеанс платы с её командами в ожидании подтверждения и доставка
прочитанного кадра прикладному слою. Кому принадлежит плата, что значит её сообщение
и когда соединение следует закрыть — решает не транспорт: за это отвечают допуск
платы и разбор её сообщений из прикладного слоя.

Чужой путь закрывается кодом `4404`, отказ в допуске — `4401`, плата, ждущая хозяина,
— `4403`, а таймаут рукопожатия — `4408`: ключа ещё не прозвучало, врать про него
нельзя. Коды остаются механикой сокета, их причину прикладной слой называет словом.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress

from websockets.asyncio.server import Server, ServerConnection, serve

from backend.application.dto.boards.board_admission import BoardOffer, BoardOwner, BoardRefusal
from backend.application.dto.boards.board_message import BoardAck
from backend.application.interfaces.services.boards.board_report import BoardReport
from backend.application.use_cases.boards.admit_board import AdmitBoardUseCase
from backend.application.use_cases.boards.route_board_message import RouteBoardMessageUseCase
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from backend.infrastructure.esp import protocol, wire
from backend.infrastructure.esp.session import (
    ACK_TIMEOUT_REASON,
    DELIVERY_FAILED_REASON,
    OFFLINE_REASON,
    BoardRegistry,
)
from backend.infrastructure.system.logging import get_logger

log = get_logger("esp.connection")

CLOSE_WRONG_PATH = 4404
CLOSE_UNKNOWN_KEY = 4401
CLOSE_AWAITING_OWNER = 4403
CLOSE_HANDSHAKE_TIMEOUT = 4408


class EspConnection:
    """Сервер, к которому дозваниваются платы, и дверь к их командам.

    Args:
        report: Приёмник, которому уходят подключения и отключения плат.
        admission: Допуск платы, который решает, кому она принадлежит.
        router: Разбор сообщений, которые плата приносит в соединении.
        host: Адрес, на котором слушает сервер.
        port: Порт, на котором слушает сервер.
        path: Путь, на который звонят платы.
        command_timeout_sec: Сколько секунд команда ждёт подтверждения.
        handshake_timeout_sec: Сколько секунд ждётся первый кадр платы.
        ping_interval_sec: Интервал служебных кадров поддержки соединения.
        ping_timeout_sec: Сколько секунд ждётся ответ на такой кадр.
        presence: Разделённый реестр подключённых плат, который транспорт обновляет.
    """

    def __init__(
        self,
        report: BoardReport,
        admission: AdmitBoardUseCase,
        router: RouteBoardMessageUseCase,
        host: str,
        port: int,
        path: str,
        command_timeout_sec: float,
        handshake_timeout_sec: float,
        ping_interval_sec: int,
        ping_timeout_sec: int,
        presence: RedisBoardPresence | None = None,
    ) -> None:
        """Инициализирует транспорт."""
        self._report = report
        self._admission = admission
        self._router = router
        self._host = host
        self._port = port
        self._path = path
        self._command_timeout = command_timeout_sec
        self._handshake_timeout = handshake_timeout_sec
        self._ping_interval = ping_interval_sec
        self._ping_timeout = ping_timeout_sec
        self._presence = presence
        self._registry = BoardRegistry()
        self._server: Server | None = None

    async def start(self) -> None:
        """Начинает слушать платы."""
        self._server = await serve(
            self._serve_client,
            self._host,
            self._port,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
        )
        log.info("esp.server_started", host=self._host, port=self._port, path=self._path)

    async def stop(self) -> None:
        """Закрывает все соединения плат и перестаёт слушать."""
        for session in self._registry.every():
            await session.close()
        self._registry.clear()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        log.info("esp.server_stopped")

    def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """True, когда у этой платы держится соединение."""
        return self._registry.is_connected(user_id, board_id)

    def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Возвращает единственную подключённую плату аккаунта."""
        return self._registry.board_for(user_id)

    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> tuple[bool, str | None]:
        """Переключает контакт и ждёт подтверждения платы.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            channel: Физический канал реле.
            energized: True замкнуть контакт, False отпустить.

        Returns:
            tuple[bool, str | None]: Подтвердила ли плата и почему нет, если нет.
        """

        def frame_of(command_id: str) -> protocol.SetRelayFrame:
            """Собирает кадр переключения канала с этим идентификатором команды."""
            return protocol.SetRelayFrame(command_id=command_id, channel=channel, state=energized)

        return await self._execute(user_id, board_id, frame_of)

    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> tuple[bool, str | None]:
        """Сообщает плате её сеть и ждёт подтверждения.

        Плата сначала пишет настройки в свою флеш-память, поэтому подтверждённая
        смена переживает перезапуск питания, даже если соединение потеряно сразу.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            profile: Сеть, в которую плате уходить.

        Returns:
            tuple[bool, str | None]: Подтвердила ли плата и почему нет, если нет.
        """

        def frame_of(command_id: str) -> protocol.SetNetworkFrame:
            """Собирает кадр смены сети с этим идентификатором команды."""
            return protocol.SetNetworkFrame(
                command_id=command_id,
                ssid=profile.ssid,
                password=profile.password,
                host=profile.host,
                server_port=profile.server_port,
                socket_port=profile.socket_port,
                socket_path=profile.socket_path,
            )

        return await self._execute(user_id, board_id, frame_of)

    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Просит плату заново сообщить всё, что она знает."""
        await self._send(user_id, board_id, protocol.GetStateFrame())

    async def confirm_ownership(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Говорит плате, что она принадлежит аккаунту.

        Подтверждение уходит в каждом успешном handshake намеренно: плата,
        пропустившая момент взятия, узнаёт о нём при следующем подключении, а
        повторная запись ничего не стоит.
        """
        await self._send(user_id, board_id, protocol.ClaimedFrame())

    async def _execute(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        frame_of: Callable[[str], protocol.SetRelayFrame | protocol.SetNetworkFrame],
    ) -> tuple[bool, str | None]:
        """Отправляет команду плате и дожидается её подтверждения.

        Плата без соединения — отказ, а не исключение: решать, что делать с
        недоступным железом, вызывающей стороне.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            frame_of: Строит кадр команды по выданному идентификатору.

        Returns:
            tuple[bool, str | None]: Подтвердила ли плата и почему нет, если нет.
        """
        session = self._registry.find(user_id, board_id)
        if session is None:
            return False, OFFLINE_REASON
        frame = frame_of(session.next_command_id())
        try:
            await session.ask(frame, self._command_timeout)
        except TimeoutError:
            return False, ACK_TIMEOUT_REASON
        except Exception as error:
            log.warning(
                "esp.command_failed",
                user=str(user_id),
                board=str(board_id),
                command=frame.type,
                error=str(error),
            )
            return False, DELIVERY_FAILED_REASON
        return True, None

    async def _send(
        self, user_id: UserId, board_id: EspDeviceId, frame: protocol.OutboundFrame
    ) -> bool:
        """Пишет кадр плате, не дожидаясь ответа.

        Returns:
            bool: True, когда кадр ушёл.
        """
        session = self._registry.find(user_id, board_id)
        if session is None:
            return False
        return await session.deliver(frame)

    async def _serve_client(self, connection: ServerConnection) -> None:
        """Принимает одно соединение платы: путь, допуск, затем разбор сообщений."""
        if not _matches_path(connection, self._path):
            await connection.close(code=CLOSE_WRONG_PATH, reason="unknown path")
            return
        raw = await self._read_first_frame(connection)
        if raw is None:
            return
        greeting = wire.read_greeting(raw)
        if greeting is None:
            await connection.close(code=CLOSE_UNKNOWN_KEY, reason="malformed handshake")
            return
        admission = await self._admission.execute(greeting)
        match admission:
            case BoardOwner(user_id=user_id, board_id=board_id):
                await self._pump(connection, user_id, board_id)
            case BoardOffer(label=label, ttl_sec=ttl_sec):
                await self._await_owner(connection, label, ttl_sec)
            case BoardRefusal(reason=reason):
                await connection.close(code=CLOSE_UNKNOWN_KEY, reason=reason)

    async def _pump(
        self, connection: ServerConnection, user_id: UserId, board_id: EspDeviceId
    ) -> None:
        """Ведёт соединение платы от допуска до его закрытия.

        Регистрирует сеанс, сообщает дому о приходе платы, просит её состояние и
        разбирает кадры, а уходя — снимает сеанс, отменяет неподтверждённые команды
        и сообщает об уходе платы.

        Args:
            connection: Соединение платы.
            user_id: Владелец платы, названный допуском.
            board_id: Идентификатор платы.
        """
        session = self._registry.open(user_id, board_id, connection)
        await self._report.on_connected(user_id, board_id)
        await self._mark_online(user_id, board_id)
        await self.confirm_ownership(user_id, board_id)
        await self.request_state(user_id, board_id)
        log.info("esp.board_connected", user=str(user_id), board=str(board_id))
        try:
            async for raw in connection:
                if isinstance(raw, bytes | bytearray):
                    log.warning(
                        "esp.unexpected_binary_message",
                        user=str(user_id),
                        board=str(board_id),
                        size=len(raw),
                    )
                    continue
                await self._refresh(user_id, board_id)
                message = wire.read_message(raw)
                if isinstance(message, BoardAck):
                    session.resolve_ack(message.command_id)
                    continue
                await self._router.execute(user_id, board_id, message)
        except Exception as error:
            log.warning(
                "esp.board_connection_failed",
                user=str(user_id),
                board=str(board_id),
                error=str(error),
            )
        finally:
            self._registry.close(session)
            session.cancel_pending()
            await self._mark_offline(user_id, board_id)
            await self._report.on_disconnected(user_id, board_id)
            log.info("esp.board_disconnected", user=str(user_id), board=str(board_id))

    async def _mark_online(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Заносит плату в общий реестр, не превращая отказ реестра в аварию сокета."""
        if self._presence is None:
            return
        with suppress(Exception):
            await self._presence.mark_online(user_id, board_id)

    async def _refresh(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Продлевает присутствие платы по признаку жизни её соединения."""
        if self._presence is None:
            return
        with suppress(Exception):
            await self._presence.refresh(user_id, board_id)

    async def _mark_offline(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Убирает плату из общего реестра при уходе её соединения."""
        if self._presence is None:
            return
        with suppress(Exception):
            await self._presence.mark_offline(user_id, board_id)

    async def _await_owner(self, connection: ServerConnection, label: str, ttl_sec: int) -> None:
        """Сообщает плате без хозяина, что её узнали, и закрывает соединение.

        Ни одной команды такой плате отправлять нельзя: она ещё никому не
        принадлежит, поэтому и закрывается кодом, по которому плата понимает, что
        ей остаётся только перепозвониться.

        Args:
            connection: Соединение не сопряжённой платы.
            label: Короткий код, который покажет интерфейс.
            ttl_sec: Сколько времени предложение остаётся действительным.
        """
        frame = protocol.ClaimFrame(label=label, ttl_sec=ttl_sec)
        with suppress(Exception):
            await connection.send(frame.to_json())
        await connection.close(code=CLOSE_AWAITING_OWNER, reason="awaiting owner")
        log.info("esp.board_awaiting_owner", label=label, ttl_sec=ttl_sec)

    async def _read_first_frame(self, connection: ServerConnection) -> str | None:
        """Ждёт первую текстовую рамку соединения.

        Таймаут и кривой кадр уже означают отказ: сокет закрывается здесь, а вызывающий
        получает None и не начинает сеанс с платой, о которой ничего не известно.

        Args:
            connection: Соединение платы.

        Returns:
            str | None: Текст первой рамки либо None, когда сеанса не будет.
        """
        try:
            raw = await asyncio.wait_for(connection.recv(), timeout=self._handshake_timeout)
        except TimeoutError:
            log.warning("esp.handshake_timeout")
            await connection.close(code=CLOSE_HANDSHAKE_TIMEOUT, reason="handshake timeout")
            return None
        except Exception as error:
            log.warning("esp.handshake_failed", error=str(error))
            return None
        if isinstance(raw, bytes | bytearray):
            log.warning(
                "esp.handshake_binary",
                size=len(raw),
                head=bytes(raw[:60]).decode("utf-8", "replace"),
            )
            return None
        return raw


def _matches_path(connection: ServerConnection, path: str) -> bool:
    """True, когда плата постучалась на путь, который сервер держит для плат."""
    request = getattr(connection, "request", None)
    actual = getattr(request, "path", None) or getattr(connection, "path", "")
    return actual in (path, f"{path}/")
