"""Сеть, которую плате предписано использовать."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SetNetworkCommand:
    """Значения запроса сменить сеть платы.

    Attributes:
        ssid: Имя беспроводной сети.
        password: Пароль этой сети; пустой, когда сеть открыта.
        host: Адрес сервера, которому плата докладывается.
        server_port: Порт обычного интерфейса этого сервера.
        socket_port: Порт доски этого сервера.
        socket_path: Путь доски этого сервера.
    """

    ssid: str
    password: str
    host: str
    server_port: int
    socket_port: int
    socket_path: str
