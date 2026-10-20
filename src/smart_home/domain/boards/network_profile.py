"""Network settings a board is told to use.

A board that was never set up knows neither the wireless network nor the address
of the server it has to report to. Both are values a person enters, either on the
page the board serves from its own access point or in the interface of the
backend, and both end up in the flash of the chip.

The value object refuses malformed input once, so a typo becomes an error the
caller can show instead of a board that never dials in.
"""

from __future__ import annotations

from dataclasses import dataclass

from smart_home.domain.exceptions import InvalidNetworkProfileError

MAX_SSID_LENGTH = 32
MAX_PASSWORD_LENGTH = 64
MAX_HOST_LENGTH = 64
MAX_PATH_LENGTH = 64
MIN_PORT = 1
MAX_PORT = 65535
DEFAULT_SERVER_PORT = 8000
DEFAULT_SOCKET_PORT = 8001
DEFAULT_SOCKET_PATH = "/ws/board"


@dataclass(frozen=True, slots=True)
class NetworkProfile:
    """The network and the server a board has to reach.

    Args:
        ssid: Name of the wireless network.
        password: Password of that network, empty when the network is open.
        host: Address of the server, a numeric one because the board resolves
            names unreliably.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.

    Returns:
        None.

    Raises:
        InvalidNetworkProfileError: When one of the values cannot be used.
    """

    ssid: str
    password: str
    host: str
    server_port: int = DEFAULT_SERVER_PORT
    socket_port: int = DEFAULT_SOCKET_PORT
    socket_path: str = DEFAULT_SOCKET_PATH

    def __post_init__(self) -> None:
        """Validate the settings of the network.

        Returns:
            None.

        Raises:
            InvalidNetworkProfileError: When one of the values cannot be used.
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
