"""Только что сопряжённая плата, у которой ключ открыт ровно один раз."""

from __future__ import annotations

from dataclasses import dataclass

from backend.application.dto.views.board_view import BoardView


@dataclass(frozen=True, slots=True)
class PairedBoardView:
    """Плата и её ключ сопряжения.

    Ответ на сопряжение несёт то, чего нет ни в одном другом ответе о плате, и именно
    поэтому это отдельный вид, а не поле в :class:`BoardView`: секрет отдаётся один раз
    и не должен появляться там, где плату просто перечисляют.

    Attributes:
        board: Плата такой, какой она сохранена.
        pairing_key: Секрет, который должна предъявлять плата.
    """

    board: BoardView
    pairing_key: str
