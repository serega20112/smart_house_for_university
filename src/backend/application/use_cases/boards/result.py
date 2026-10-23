"""Результаты сценариев работы с платами."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.boards.board_view import BoardView


@dataclass(frozen=True, slots=True)
class PairedBoard:
    """Только что сопряжённая плата и её ключ.

    Attributes:
        board: Плата такой, какой она сохранена.
        pairing_key: Секрет, который должна предъявлять плата; отдаётся ровно раз.
    """

    board: BoardView
    pairing_key: str
