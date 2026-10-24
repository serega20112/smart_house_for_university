"""Поток событий для тех, кто смотрит дом прямо сейчас."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.domain.identifiers import UserId


class RealtimePublisher(ABC):
    """Отдаёт событие тем, кто наблюдает за домом."""

    @abstractmethod
    async def publish(self, user_id: UserId, event: str, payload: dict[str, Any]) -> None:
        """Отправляет событие клиентам одного аккаунта."""

    @abstractmethod
    async def broadcast(self, event: str, payload: dict[str, Any]) -> None:
        """Отправляет событие всем подключённым клиентам.

        Плата, которая ещё никому не принадлежит, — ровно такой факт: она ни к
        чьему аккаунту не относится, поэтому её объявляют всем, а не перебирают
        аккаунты.
        """
