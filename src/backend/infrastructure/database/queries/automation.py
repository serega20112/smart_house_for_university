"""Чтения настройки автоматизации.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.dto.views.automation_view import AutomationView
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.infrastructure.database.mappers.automation import automation_from_row
from backend.infrastructure.database.models import (
    AutomationModel,
)
from backend.infrastructure.database.repositories.base import first_row
from backend.infrastructure.database.repositories.child_rows import (
    participants_of,
)


class SqlAutomationQueries:
    """Чтения настройки автоматизации без явной транзакции.

    Чтения идут через сессию, а не через голое соединение: только сессия гидратирует
    ORM-сущности, и потому `select(AutomationModel)` отдаёт строку-настройку, а не
    первый столбец.

    Attributes:
        session_factory: Фабрика сессий, на которой выполняют чтения.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует чтения.

        Args:
            session_factory: Фабрика сессий, из которой читают.
        """
        self._session_factory = session_factory

    async def get(self, user_id: UserId) -> AutomationView:
        """Возвращает настройку автоматизации аккаунта.

        Аккаунт, который автоматизацию ни разу не настраивал, ответ всё равно получает:
        значения по умолчанию берутся из самого агрегата, поэтому модель чтения не
        расходится с тем, из чего на деле строят свежий дом.

        Args:
            user_id: Владелец настройки.

        Returns:
            AutomationView: Настройка, приготовленная для показа.
        """
        async with self._session_factory() as session:
            row = await first_row(
                session, AutomationModel, AutomationModel.user_id == user_id.value
            )
            participants = await participants_of(session, user_id)
        if row is None:
            return automation_view_of(AutomationSettings.create(user_id), frozenset())
        return automation_view_of(automation_from_row(row, participants), participants)


def automation_view_of(
    settings: AutomationSettings, participants: frozenset[DeviceId]
) -> AutomationView:
    """Возвращает модель чтения одной настройки автоматизации.

    Args:
        settings: Настройка, из которой строят образ.
        participants: Устройства, которыми автоматизации разрешено управлять.

    Returns:
        AutomationView: Настройка, приготовленная для показа.
    """
    return AutomationView(
        enabled=settings.enabled,
        target_temperature=settings.target_temperature.celsius,
        target_humidity=settings.target_humidity.percent,
        temperature_tolerance=settings.temperature_tolerance,
        humidity_tolerance=settings.humidity_tolerance,
        participating_device_ids=participants,
    )
