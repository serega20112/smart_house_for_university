"""Читающая сторона плат."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.application.dto.views.board_claim_view import BoardClaimView
from backend.application.dto.views.board_view import BoardView
from backend.domain.identifiers import UserId


class BoardQueries(Protocol):
    """Чтения плат."""

    async def list_all(self, user_id: UserId) -> list[BoardView]:
        """Возвращает все платы аккаунта."""

    async def list_open_claims(self, now: datetime) -> list[BoardClaimView]:
        """Возвращает предложения, которые ещё никто не взяли и срок которых не истёк.

        Просроченное объявление не показывается: плата перестала его держать, а
        значит, и забрать его уже нельзя. Удаляет же истёкшие строки отдельная
        команда фонового рабочего — чтение базу не меняет.
        """
