"""Хранилище настроек автоматизации PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import (
    ConcurrentModificationError,
)
from backend.application.interfaces.repositories.automation_repository import AutomationRepository
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import (
    UserId,
)
from backend.infrastructure.database.mappers.automation import (
    automation_from_row,
    automation_to_row,
    participant_rows,
)
from backend.infrastructure.database.models import (
    AutomationModel,
    AutomationParticipantModel,
)
from backend.infrastructure.database.repositories.base import (
    affected_rows,
    first_row,
    insert_rows,
    row_values,
    upsert_columns,
)
from backend.infrastructure.database.repositories.child_rows import participants_of

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlAutomationRepository(AutomationRepository):
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
        row = await first_row(
            self._session, AutomationModel, AutomationModel.user_id == user_id.value
        )
        if row is None:
            return None
        return automation_from_row(row, await participants_of(self._session, user_id))

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
        refreshed = upsert_columns(AutomationModel.__table__, "user_id", "version")
        refreshed["version"] = settings.version + 1
        values = row_values(AutomationModel.__table__, automation_to_row(settings))
        result = await self._session.execute(
            postgresql.insert(AutomationModel.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[AutomationModel.__table__.c.user_id],
                set_=refreshed,
                where=AutomationModel.version == settings.version,
            )
        )
        await self._session.flush()
        if not affected_rows(result):
            raise ConcurrentModificationError("automation", settings.user_id)
        settings.version += 1
        await self._session.execute(
            delete(AutomationParticipantModel).where(
                AutomationParticipantModel.user_id == settings.user_id.value
            )
        )
        await insert_rows(
            self._session,
            AutomationParticipantModel.__table__,
            participant_rows(settings),
        )
        await self._session.flush()
