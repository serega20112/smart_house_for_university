"""Список плат, которые ждут своего аккаунта."""

from __future__ import annotations

from backend.application.interface.queries.board_queries import BoardQueries
from backend.domain.value_objects.boards.board_claim_view import BoardClaimView


class ListBoardClaimsUseCase:
    """Показывает объявления плат, которые ещё никто не забрал."""

    def __init__(self, queries: BoardQueries) -> None:
        """Собирает сценарий списка предложений.

        Args:
            queries: Чтения плат и их предложений.
        """
        self._queries = queries

    async def execute(self) -> list[BoardClaimView]:
        """Возвращает открытые предложения.

        Список одинаков для всех аккаунтов: плата объявляется серверу, а не
        человеку. Безопасным его делает то, что предложение живёт, пока плату
        держат, и первый забравший выигрывает.

        Returns:
            list[BoardClaimView]: Предложения с токеном, кодом и сроком.
        """
        return await self._queries.list_open_claims()
