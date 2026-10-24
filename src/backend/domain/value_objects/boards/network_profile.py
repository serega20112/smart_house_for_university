"""Сеть, которую плате предписано использовать.

Плата, которую ни разу не настраивали, не знает ни беспроводной сети, ни адреса
сервера, которому она должна докладываться. Оба значения вводит человек — на странице,
которую плата сама отдаёт со своей точки доступа, или в интерфейсе бэкенда, — и оба
оседают в памяти чипа.

Объект-значение один раз отвергает неподходящие значения, поэтому опечатка становится
видимой вызывающему ошибкой, а не платой, которая никогда не дозвонится.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidNetworkProfileError

MAX_SSID_LENGTH = 32
MAX_PASSWORD_LENGTH = 64
MAX_HOST_LENGTH = 64
MAX_PATH_LENGTH = 64
MIN_PORT = 1
MAX_PORT = 65535


@dataclass(frozen=True, slots=True)
class NetworkProfile:
    """Сеть и сервер, до которых плате надо добраться.

    Attributes:
        ssid: Имя беспроводной сети.
        password: Пароль этой сети; пустой, когда сеть открыта.
        host: Адрес сервера — числовой, потому что имена плата разрешает ненадёжно.
        server_port: Порт обычного интерфейса этого сервера.
        socket_port: Порт WebSocket-сервера плат на этом сервере.
        socket_path: Путь WebSocket-сервера плат на этом сервере.

    Raises:
        InvalidNetworkProfileError: Когда одно из значений применить нельзя.
    """

    ssid: str
    password: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str

    def __post_init__(self) -> None:
        """Проверяет настройки сети.

        Raises:
            InvalidNetworkProfileError: Когда одно из значений применить нельзя.
        """
        ssid = self.ssid.strip()
        if not ssid:
            raise InvalidNetworkProfileError("the name of the network is empty")
        if len(ssid) > MAX_SSID_LENGTH:
            raise InvalidNetworkProfileError("the name of the network is too long")
        if len(self.password) > MAX_PASSWORD_LENGTH:
            raise InvalidNetworkProfileError("the password of the network is too long")

        host = self.host.strip()
        if not host:
            raise InvalidNetworkProfileError("the address of the server is empty")
        if len(host) > MAX_HOST_LENGTH:
            raise InvalidNetworkProfileError("the address of the server is too long")

        if not MIN_PORT <= self.server_port <= MAX_PORT:
            raise InvalidNetworkProfileError("the port of the server is out of range")
        if not MIN_PORT <= self.socket_port <= MAX_PORT:
            raise InvalidNetworkProfileError("the port of the board socket is out of range")

        path = self.socket_path.strip()
        if not path.startswith("/"):
            raise InvalidNetworkProfileError(
                "the path of the board socket has to start with a slash"
            )
        if len(path) > MAX_PATH_LENGTH:
            raise InvalidNetworkProfileError("the path of the board socket is too long")

        object.__setattr__(self, "ssid", ssid)
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "socket_path", path)
