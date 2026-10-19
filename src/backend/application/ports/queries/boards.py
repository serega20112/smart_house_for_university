"""Read side of the boards."""

from __future__ import annotations

from typing import Protocol

from backend.application.dto.esp import BoardClaimView, BoardView
from backend.domain.identifiers import UserId


class BoardQueries(Protocol):
    """Reads of the boards."""

    async def list_for(self, user_id: UserId) -> list[BoardView]:
        """Return every board of an account.

        Args:
            user_id: Owner of the boards.

        Returns:
            list[BoardView]: Boards shaped for display.
        """

    async def list_open_claims(self) -> list[BoardClaimView]:
        """Return every offer nobody took yet.

        Reading the list never deletes anything: removing what is over is a
        separate command the background worker runs.

        Returns:
            list[BoardClaimView]: Open offers.
        """
