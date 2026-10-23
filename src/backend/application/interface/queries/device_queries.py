"""Читающая сторона устройств."""

from __future__ import annotations

from typing import Protocol

from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.devices.device_view import DeviceView


class DeviceQueries(Protocol):
    """Чтения конфигурации устройств.

    Запрос отдаёт плоскую строку, готовую для показа, а не агрегат: экрану не
    нужно обходить устройство по полям, и чтение не открывает транзакцию.
    """

    async def list_all(self, user_id: UserId) -> list[DeviceView]:
        """Возвращает все устройства аккаунта."""

    async def get(self, user_id: UserId, device_id: DeviceId) -> DeviceView | None:
        """Возвращает одно устройство аккаунта."""
