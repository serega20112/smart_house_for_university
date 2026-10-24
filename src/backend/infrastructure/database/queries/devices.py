"""Чтения настройки устройств.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.device_view import DeviceView
from backend.infrastructure.database.repositories.base import every_row, first_row
from backend.infrastructure.database.repositories.child_rows import (
    capabilities_of,
)
from backend.infrastructure.database.tables import (
    DeviceRow,
)


class SqlDeviceQueries:
    """Чтения настройки устройств без транзакции.

    Attributes:
        engine: Движок, на котором выполняют чтения.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Инициализирует чтения.

        Args:
            engine: Движок, из которого читают.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[DeviceView]:
        """Возвращает все устройства аккаунта.

        Args:
            user_id: Владелец устройств.

        Returns:
            list[DeviceView]: Устройства, приготовленные для показа.
        """
        async with self._engine.connect() as connection:
            rows = await every_row(connection, DeviceRow, DeviceRow.user_id == user_id.value)
            stored = await capabilities_of(connection, [row.id for row in rows])
        return [device_view_of(row, stored.get(row.id, frozenset())) for row in rows]

    async def get(self, user_id: UserId, device_id: DeviceId) -> DeviceView | None:
        """Возвращает одно устройство аккаунта.

        Args:
            user_id: Владелец устройства.
            device_id: Идентификатор устройства.

        Returns:
            DeviceView | None: Устройство или None, когда у аккаунта такого нет.
        """
        async with self._engine.connect() as connection:
            row = await first_row(
                connection,
                DeviceRow,
                DeviceRow.id == device_id.value,
                DeviceRow.user_id == user_id.value,
            )
            if row is None:
                return None
            stored = await capabilities_of(connection, [row.id])
        return device_view_of(row, stored.get(row.id, frozenset()))


def device_view_of(row: DeviceRow, capabilities: frozenset[Capability]) -> DeviceView:
    """Возвращает модель чтения одного сохранённого устройства.

    Устройство показывается выключенным: его логическое состояние относится к живому
    слою железа, а не к строке таблицы.

    Args:
        row: Строка, которую превращают в образ.
        capabilities: Способности, прочитанные из таблицы способностей.

    Returns:
        DeviceView: Устройство, приготовленное для показа.
    """
    return DeviceView(
        id=DeviceId.parse(row.id),
        name=row.name,
        kind=DeviceKind.parse(row.kind),
        channel=row.channel,
        capabilities=capabilities,
        enabled=row.enabled,
        automation_enabled=row.automation_enabled,
        status=DeviceStatus.OFF,
    )
