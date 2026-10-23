"""The network a board is told to use."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SetNetworkCommand:
    """The values of a network change the interface is asked to perform.

    Args:
        ssid: Name of the wireless network.
        password: Password of that network, empty when the network is open.
        host: Address of the server the board reports to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.

    Returns:
        None.
    """

    ssid: str
    password: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str
