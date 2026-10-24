"""Список плат аккаунта с их живой доступностью."""

from __future__ import annotations

from dataclasses import replace

from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.domain.identifiers import UserId
from backend.domain.value_objects.boards.board_view import BoardView


class ListBoardsUseCase:
    """Показывает платы аккаунта так, какие они сейчас."""

    def __init__(self, queries: BoardQueries, gateway: BoardGateway) -> None:
        """Собирает сценарий списка плат.

        Args:
            queries: Чтения сохранённых плат.
            gateway: Живой транспорт, который знает, подключена ли плата.
        """
        self._queries = queries
        self._gateway = gateway

    async def execute(self, user_id: UserId) -> list[BoardView]:
        """Возвращает платы аккаунта.

        Строка таблицы не знает, есть ли сейчас соединение, поэтому признак
        `online` берётся у транспорта, а не из хранилища.

        Args:
            user_id: Владелец плат.

        Returns:
            list[BoardView]: Платы аккаунта с живой доступностью.
        """
        boards = await self._queries.list_all(user_id)
        return [
            replace(board, online=self._gateway.is_connected(user_id, board.id)) for board in boards
        ]
