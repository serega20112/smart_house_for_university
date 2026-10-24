"""Хранилище настроек автоматизации PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import (
    ConcurrentModificationError,
)
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row, insert_rows, upsert_columns
from backend.infrastructure.database.repositories.child_rows import participants_of
from backend.infrastructure.database.tables import (
    AutomationParticipantRow,
    AutomationRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlAutomationRepository:
    """Хранение настройки автоматизации одного аккаунта.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def get(self, user_id: UserId) -> AutomationSettings | None:
        """Возвращает сохранённую настройку.

        У аккаунта, который автоматизацию ни разу не настраивал, строки нет, и здесь
        возвращают None вместо того, чтобы её завести.

        Args:
            user_id: Владелец настройки.

        Returns:
            AutomationSettings | None: Сохранённая настройка или None, когда
                аккаунт автоматизацию не настраивал.
        """
        row = await first_row(self._session, AutomationRow, AutomationRow.user_id == user_id.value)
        if row is None:
            return None
        return mappers.automation_from_row(row, await participants_of(self._session, user_id))

    async def save(self, settings: AutomationSettings) -> None:
        """Сохраняет настройку автоматизации аккаунта.

        Строку пишут через upsert, поэтому сохранить настройку дважды за одну сессию —
        не столкнуть её саму с собой. Существующую строку обновляют только тогда, когда
        этот записывающий прочитал ту ревизию, что в строке и сейчас: устаревший
        записывающий не меняет ничего, вместо того чтобы перетереть более новую настройку.

        Args:
            settings: Настройка для записи.

        Raises:
            ConcurrentModificationError: Когда строка ушла вперёд с момента чтения.
        """
        refreshed = upsert_columns(AutomationRow.__table__, "user_id", "version")
        refreshed["version"] = settings.version + 1
        values = mappers.row_values(AutomationRow.__table__, mappers.automation_to_row(settings))
        result = await self._session.execute(
            postgresql.insert(AutomationRow.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[AutomationRow.__table__.c.user_id],
                set_=refreshed,
                where=AutomationRow.version == settings.version,
            )
        )
        await self._session.flush()
        if not result.rowcount:
            raise ConcurrentModificationError("automation", settings.user_id)
        settings.version += 1
        await self._session.execute(
            delete(AutomationParticipantRow).where(
                AutomationParticipantRow.user_id == settings.user_id.value
            )
        )
        await insert_rows(
            self._session,
            AutomationParticipantRow.__table__,
            mappers.participant_rows(settings),
        )
        await self._session.flush()
