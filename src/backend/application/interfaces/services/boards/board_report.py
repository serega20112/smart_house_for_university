"""Приёмник сообщений, которые плата приносит во время соединения."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading


class BoardReport(ABC):
    """Всё, что одна плата сообщает, пока подключена."""

    @abstractmethod
    async def on_connected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Плата только что подключилась."""

    @abstractmethod
    async def on_disconnected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Соединение с платой потеряно."""

    @abstractmethod
    async def on_relay_states(
        self, user_id: UserId, board_id: EspDeviceId, states: Sequence[bool]
    ) -> None:
        """Плата сообщила положения реле."""

    @abstractmethod
    async def on_reading(
        self, user_id: UserId, board_id: EspDeviceId, reading: ClimateReading
    ) -> None:
        """Плата сообщила показания датчиков."""

    @abstractmethod
    async def on_error(
        self, user_id: UserId, board_id: EspDeviceId, code: str, message: str
    ) -> None:
        """Плата сообщила ошибку."""
