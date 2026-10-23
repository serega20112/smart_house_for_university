"""Поведение устройств при изменении их описания."""

from __future__ import annotations

import os


def device_refresh_attempts() -> int:
    """Сколько раз перечитывается устройство после его изменения.

    Returns:
        int: Число попыток.
    """
    return int(os.getenv("DEVICE_REFRESH_ATTEMPTS", "3"))
