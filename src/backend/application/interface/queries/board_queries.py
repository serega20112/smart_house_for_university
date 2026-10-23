"""Читающая сторона плат."""

from __future__ import annotations

from typing import Protocol

from backend.domain.identifiers import UserId
from backend.domain.value_objects.boards.board_claim_view import BoardClaimView
from backend.domain.value_objects.boards.board_view import BoardView


class BoardQueries(Protocol):
    """Чтения плат."""

    async def list_all(self, user_id: UserId) -> list[BoardView]:
        """Возвращает все платы аккаунта."""

    async def list_open_claims(self) -> list[BoardClaimView]:
        """Возвращает предложения, которые ещё никто не взял.

        Чтение списка ничего не удаляет: убрать истёкшее — отдельная команда,
        которую запускает фоновый рабочий.
        """
