"""
Сеть, которую плате предписано использовать.

Это сущность платы, а не отдельный агрегат: сеть принадлежит одной плате и не
изменяется вне неё. То, о чём сообщает сама плата, живёт в её состоянии, а здесь
лежит то, что попросил владелец, — значения расходятся, пока изменение в пути.
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
