"""Чтения настройки устройств.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.dto.views.device_view import DeviceView
from backend.domain.identifiers import (
    DeviceId,
    EspDeviceId,
    UserId,
)
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.infrastructure.database.models import (
    DeviceModel,
)
from backend.infrastructure.database.repositories.base import every_row, first_row
from backend.infrastructure.database.repositories.child_rows import (
    capabilities_of,
)


class SqlDeviceQueries:
    """Чтения настройки устройств без явной транзакции.

    Чтения идут через сессию, а не через голое соединение: только сессия гидратирует
    ORM-сущности, и потому `select(DeviceModel)` отдаёт строку-устройство, а не первый
    столбец.

    Attributes:
        session_factory: Фабрика сессий, на которой выполняют чтения.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует чтения.

        Args:
            session_factory: Фабрика сессий, из которой читают.
        """
        self._session_factory = session_factory

    async def list_all(self, user_id: UserId) -> list[DeviceView]:
        """Возвращает все устройства аккаунта.

        Args:
            user_id: Владелец устройств.

        Returns:
            list[DeviceView]: Устройства, приготовленные для показа.
        """
        async with self._session_factory() as session:
            rows = await every_row(session, DeviceModel, DeviceModel.user_id == user_id.value)
            stored = await capabilities_of(session, [row.id for row in rows])
        return [device_view_of(row, stored.get(row.id, frozenset())) for row in rows]

    async def get(self, user_id: UserId, device_id: DeviceId) -> DeviceView | None:
        """Возвращает одно устройство аккаунта.

        Args:
            user_id: Владелец устройства.
            device_id: Идентификатор устройства.

        Returns:
            DeviceView | None: Устройство или None, когда у аккаунта такого нет.
        """
        async with self._session_factory() as session:
            row = await first_row(
                session,
                DeviceModel,
                DeviceModel.id == device_id.value,
                DeviceModel.user_id == user_id.value,
            )
            if row is None:
                return None
            stored = await capabilities_of(session, [row.id])
        return device_view_of(row, stored.get(row.id, frozenset()))


def device_view_of(row: DeviceModel, capabilities: frozenset[Capability]) -> DeviceView:
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
        board_id=None if row.board_id is None else EspDeviceId.parse(row.board_id),
    )
