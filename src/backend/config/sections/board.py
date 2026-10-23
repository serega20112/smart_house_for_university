"""Транспорт, в который звонят платы, и сроки его работы."""

from __future__ import annotations

import os


def board_socket_port() -> int:
    """Порт транспорта плат.

    Returns:
        int: Порт прослушивания.
    """
    return int(os.getenv("BOARD_SOCKET_PORT", "8001"))


def board_socket_path() -> str:
    """Путь транспорта плат.

    Returns:
        str: Путь запроса подключения.
    """
    return os.getenv("BOARD_SOCKET_PATH", "/ws/board")


def board_command_timeout_sec() -> float:
    """Сколько времени у платы подтвердить команду.

    Returns:
        float: Секунды ожидания подтверждения.
    """
    return float(os.getenv("BOARD_COMMAND_TIMEOUT_SEC", "5.0"))


def board_watchdog_sec() -> float:
    """Сколько плата может молчать, оставаясь доступной.

    Returns:
        float: Секунды молчания до потери.
    """
    return float(os.getenv("BOARD_WATCHDOG_SEC", "15.0"))


def board_claim_ttl_sec() -> int:
    """Сколько живёт предложение неподключённой платы.

    Returns:
        int: Секунды действия предложения.
    """
    return int(os.getenv("BOARD_CLAIM_TTL_SEC", "120"))


def board_handshake_timeout_sec() -> float:
    """Сколько ждём первое сообщение от позвонившей платы.

    Returns:
        float: Секунды ожидания рукопожатия.
    """
    return float(os.getenv("BOARD_HANDSHAKE_TIMEOUT_SEC", "10.0"))


def board_ping_interval_sec() -> int:
    """Как часто транспорт отправляет платам контрольные кадры.

    Returns:
        int: Интервал в секундах.
    """
    return int(os.getenv("BOARD_PING_INTERVAL_SEC", "30"))


def board_ping_timeout_sec() -> int:
    """Как долго ждём ответ на контрольный кадр.

    Returns:
        int: Секунды до разрыва молчащего соединения.
    """
    return int(os.getenv("BOARD_PING_TIMEOUT_SEC", "45"))
