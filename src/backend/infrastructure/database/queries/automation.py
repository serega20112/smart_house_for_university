"""Чтения настройки автоматизации.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.domain.value_objects.automation.automation_view import AutomationView
from backend.infrastructure.database.mappers.automation import automation_from_row
from backend.infrastructure.database.models import (
    AutomationModel,
)
from backend.infrastructure.database.repositories.base import first_row
from backend.infrastructure.database.repositories.child_rows import (
    participants_of,
)


class SqlAutomationQueries:
    """Чтения настройки автоматизации без транзакции.

    Attributes:
        engine: Движок, на котором выполняют чтения.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Инициализирует чтения.

        Args:
            engine: Движок, из которого читают.
        """
        self._engine = engine

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
        async with self._engine.connect() as connection:
            row = await first_row(
                connection, AutomationModel, AutomationModel.user_id == user_id.value
            )
            participants = await participants_of(connection, user_id)
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
