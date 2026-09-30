"""ESP8266 gateway settings."""

from __future__ import annotations

import os


def server_host() -> str:
    """Return the bind host of the ESP WebSocket server.

    Returns:
        str: Bind host.
    """
    return os.getenv("ESP_SERVER_HOST", "0.0.0.0")


def server_port() -> int:
    """Return the bind port of the ESP WebSocket server.

    Returns:
        int: Bind port.
    """
    return int(os.getenv("ESP_SERVER_PORT", "8765"))


def server_path() -> str:
    """Return the WebSocket path the ESP8266 connects to.

    Returns:
        str: WebSocket path.
    """
    return os.getenv("ESP_SERVER_PATH", "/esp")


def command_timeout_sec() -> float:
    """Return how long a relay command waits for its acknowledgement.

    Returns:
        float: Timeout in seconds.
    """
    return float(os.getenv("ESP_COMMAND_TIMEOUT_SEC", "5.0"))


def watchdog_sec() -> float:
    """Return the silence window after which the board counts as unavailable.

    Returns:
        float: Timeout in seconds.
    """
    return float(os.getenv("ESP_WATCHDOG_SEC", "15.0"))
