"""Плата в том виде, в каком её показывает экран."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.identifiers import EspDeviceId


@dataclass(frozen=True, slots=True)
class BoardView:
    """Описание платы для интерфейса.

    Ключ сопряжения здесь отсутствует намеренно: это credential, которому не
    место в списке плат. Он отдаётся ровно один раз — самой операцией сопряжения.

    Attributes:
        id: Идентификатор платы.
        name: Имя, которое видно пользователю.
        online: Подключена ли плата прямо сейчас.
        last_seen_at: Момент последнего успешного рукопожатия или None.
        current_ssid: Сеть, о которой сообщила плата, или None.
    """

    id: EspDeviceId
    name: str
    online: bool
    last_seen_at: datetime | None
    current_ssid: str | None = None
