"""Читает весь дом одного аккаунта одним снимком для главного экрана.

Экран показывает климат, устройства, автоматику и идущие сценарии сразу. Сборку этих
четырёх источников в одну проекцию ведёт `HomeOverviewQuery` — тот же самый, что питает
текстовую команду о состоянии дома, — поэтому здесь остаётся только отдать готовое.
"""

from __future__ import annotations

from backend.application.dto.views.home_snapshot_view import HomeSnapshotView
from backend.application.services.home_overview import HomeOverviewQuery
from backend.domain.identifiers import UserId


class ReadHomeSnapshotUseCase:
    """Возвращает всё, что показывает главный экран интерфейса."""

    def __init__(self, overview: HomeOverviewQuery) -> None:
        """Инициализирует сценарий.

        Args:
            overview: Единый сборщик читающей проекции дома.
        """
        self._overview = overview

    async def execute(self, user_id: UserId) -> HomeSnapshotView:
        """Возвращает снимок дома одного аккаунта.

        Args:
            user_id: Владелец дома.

        Returns:
            HomeSnapshotView: Всё, что интерфейсу надо нарисовать.
        """
        return await self._overview.load(user_id)
