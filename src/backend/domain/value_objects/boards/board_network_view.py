"""Сеть платы в том виде, в каком её показывает экран."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import EspDeviceId
from backend.domain.value_objects.boards.network_profile import NetworkProfile


@dataclass(frozen=True, slots=True)
class BoardNetworkView:
    """Сетевые настройки платы для интерфейса.

    Пароля здесь нет намеренно: секрет не должен попадать на экран, плата хранит
    его в собственной флеш-памяти.

    Attributes:
        board_id: Идентификатор платы.
        ssid: Имя беспроводной сети, которое плате предписано использовать.
        host: Адрес сервера, которому плата должна отчитываться.
        server_port: Порт обычного интерфейса этого сервера.
        socket_port: Порт сокета плат этого сервера.
        socket_path: Путь сокета плат этого сервера.
        configured: Есть ли у платы уже собственная сеть.
        updated_at: Момент записи настроек или None.
    """

    board_id: EspDeviceId
    ssid: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str
    configured: bool
    updated_at: datetime | None

    @classmethod
    def of(
        cls,
        board_id: EspDeviceId,
        profile: NetworkProfile,
        updated_at: datetime | None,
    ) -> BoardNetworkView:
        """Собирает представление сети из сохранённого профиля.

        Единственное место, где сеть платы превращается в форму для экрана, —
        поэтому показ после записи и показ из хранилища не начинают расходиться.

        Args:
            board_id: Идентификатор платы.
            profile: Сеть, предписанная плате.
            updated_at: Момент записи настроек или None.

        Returns:
            BoardNetworkView: Сеть платы для интерфейса.
        """
        return cls(
            board_id=board_id,
            ssid=profile.ssid,
            host=profile.host,
            server_port=profile.server_port,
            socket_port=profile.socket_port,
            socket_path=profile.socket_path,
            configured=True,
            updated_at=updated_at,
        )
