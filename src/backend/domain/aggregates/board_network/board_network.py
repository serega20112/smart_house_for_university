"""Сеть, которую плате предписано использовать.

Плата, настроившаяся сама, уже знает сеть, и бэкенд узнаёт её из handshake. Этот
агрегат — вторая половина: сеть, которую владелец попросил в интерфейсе и которую
бэкенд передаёт плате.

Держать их врозь — намеренно. То, о чём сообщает плата, есть то, где она находится
сейчас и живёт вместе с платой; это же — где ей над быть, и значения расходятся, пока
изменение в пути.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile


@dataclass(frozen=True, slots=True)
class BoardNetwork:
    """Сеть, которую должна использовать одна плата.

    Attributes:
        board_id: Плата, к которой относится сеть.
        user_id: Владелец платы.
        profile: Настройки, которые бэкенд велел плате применить.
        updated_at: Момент записи настроек.
    """

    board_id: EspDeviceId
    user_id: UserId
    profile: NetworkProfile
    updated_at: datetime
