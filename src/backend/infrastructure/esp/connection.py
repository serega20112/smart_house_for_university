"""WebSocket-транспорт между бэкендом и платами.

Бэкенд слушает, а каждая плата дозванивается сама как клиент: плата в любой
домашней сети достигает сервера в интернете, не требуя входящих соединений.

Всё, что нужно транспорту извне, приходит в конструктор: приёмник сообщений плат
и шлюз, отвечающий на вопросы handshake. Ничего не подвязывается после сборки,
поэтому сеанс платы описывается её аргументами, и тест собирает его без сокета.

Разбор первого кадра живёт в :mod:`handshake`, перевод входящих кадров —
в :mod:`inbound`, а сеансы с их командами — в :mod:`session`; здесь остаётся
сервер и дверь к командам платы.
"""

from __future__ import annotations

from collections.abc import Callable

from websockets.asyncio.server import Server, ServerConnection, serve

from backend.application.interface.services.board_report import BoardReport
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.esp import handshake, inbound, protocol
from backend.infrastructure.esp.onboarding import BoardIdentity, BoardOnboardingGateway
from backend.infrastructure.esp.session import (
    ACK_TIMEOUT_REASON,
    DELIVERY_FAILED_REASON,
    OFFLINE_REASON,
    BoardRegistry,
)
from backend.infrastructure.logging import get_logger

log = get_logger("esp.connection")


class EspConnection:
    """Сервер, к которому дозваниваются платы, и дверь к их командам.

    Args:
        report: Приёмник, которому уходят сообщения всех плат.
        onboarding: Шлюз, отвечающий на вопросы handshake.
        host: Адрес, на котором слушает сервер.
        port: Порт, на котором слушает сервер.
        path: Путь, на который звонят платы.
        command_timeout_sec: Сколько секунд команда ждёт подтверждения.
        handshake_timeout_sec: Сколько секунд ждётся первый кадр платы.
        ping_interval_sec: Интервал служебных кадров поддержки соединения.
        ping_timeout_sec: Сколько секунд ждётся ответ на такой кадр.
    """

    def __init__(
        self,
        report: BoardReport,
        onboarding: BoardOnboardingGateway,
        host: str,
        port: int,
        path: str,
        command_timeout_sec: float,
        handshake_timeout_sec: float,
        ping_interval_sec: int,
        ping_timeout_sec: int,
    ) -> None:
        """Инициализирует транспорт.

        Args:
            report: Приёмник, которому уходят сообщения всех плат.
            onboarding: Шлюз, отвечающий на вопросы handshake.
            host: Адрес, на котором слушает сервер.
            port: Порт, на котором слушает сервер.
            path: Путь, на который звонят платы.
            command_timeout_sec: Сколько секунд команда ждёт подтверждения.
            handshake_timeout_sec: Сколько секунд ждётся первый кадр платы.
            ping_interval_sec: Интервал служебных кадров поддержки соединения.
            ping_timeout_sec: Сколько секунд ждётся ответ на такой кадр.
        """
        self._report = report
        self._onboarding = onboarding
        self._host = host
        self._port = port
        self._path = path
        self._command_timeout = command_timeout_sec
        self._handshake_timeout = handshake_timeout_sec
        self._ping_interval = ping_interval_sec
        self._ping_timeout = ping_timeout_sec
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
        """Принимает одно соединение платы: путь, handshake, затем разбор кадров."""
        if not handshake.matches_path(connection, self._path):
            await connection.close(code=handshake.CLOSE_WRONG_PATH, reason="unknown path")
            return
        identity = await handshake.greet(connection, self._onboarding, self._handshake_timeout)
        if identity is None:
            return
        await self._pump(connection, identity)

    async def _pump(self, connection: ServerConnection, identity: BoardIdentity) -> None:
        """Ведёт соединение платы от handshake до его закрытия.

        Регистрирует сеанс, сообщает дому о приходе платы, просит её состояние и
        разбирает кадры, а уходя — снимает сеанс, отменяет неподтверждённые команды
        и сообщает об уходе платы.

        Args:
            connection: Соединение платы.
            identity: Владелец и идентификатор, полученные в handshake.
        """
        session = self._registry.open(identity.user_id, identity.board_id, connection)
        await self._report.on_connected(identity.user_id, identity.board_id)
        await self.confirm_ownership(identity.user_id, identity.board_id)
        await self.request_state(identity.user_id, identity.board_id)
        log.info("esp.board_connected", user=str(identity.user_id), board=str(identity.board_id))
        try:
            async for raw in connection:
                if isinstance(raw, bytes | bytearray):
                    log.warning(
                        "esp.unexpected_binary_message",
                        user=str(identity.user_id),
                        board=str(identity.board_id),
                        size=len(raw),
                    )
                else:
                    await inbound.read(session, raw, self._report)
        except Exception as error:
            log.warning(
                "esp.board_connection_failed",
                user=str(identity.user_id),
                board=str(identity.board_id),
                error=str(error),
            )
        finally:
            self._registry.close(session)
            session.cancel_pending()
            await self._report.on_disconnected(identity.user_id, identity.board_id)
            log.info(
                "esp.board_disconnected",
                user=str(identity.user_id),
                board=str(identity.board_id),
            )
