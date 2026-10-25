"""Список плат, которые ждут своего аккаунта."""

from __future__ import annotations

from backend.application.dto.views.board_claim_view import BoardClaimView
from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.services.system.clock import Clock


class ListBoardClaimsUseCase:
    """Показывает объявления плат, которые ещё никто не забрал."""

    def __init__(self, queries: BoardQueries, clock: Clock) -> None:
        """Собирает сценарий списка предложений.

        Args:
            queries: Чтения плат и их предложений.
            clock: Источник текущего времени: предложение открыто ровно до своего срока.
        """
        self._queries = queries
        self._clock = clock

    async def execute(self) -> list[BoardClaimView]:
        """Возвращает открытые предложения.

        Список одинаков для всех аккаунтов: плата объявляется серверу, а не
        человеку. Безопасным его делает то, что предложение живёт, пока плату
        держат, и первый забравший выигрывает. Просроченное объявление уходит из
        списка в тот же момент, когда оно перестаёт быть действительным, — поэтому
        интерфейс не предлагает забрать то, что взять уже нельзя.

        Returns:
            list[BoardClaimView]: Предложения с токеном, кодом и сроком.
        """
        return await self._queries.list_open_claims(self._clock.now())
