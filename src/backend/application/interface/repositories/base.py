"""Базовые операции репозиториев.

Каждая операция — отдельный маленький интерфейс, поэтому репозиторий фичи
наследует ровно то, что умеет его хранилище, и не выдумывает метод `delete` там,
где удаление не предусмотрено.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from backend.domain.identifiers import UserId


class Creator[E](ABC):
    """Записывает новый объект."""

    @abstractmethod
    async def add(self, entity: E) -> None:
        """Сохраняет созданный объект."""


class Updater[E](ABC):
    """Перезаписывает изменённый объект."""

    @abstractmethod
    async def update(self, entity: E) -> None:
        """Сохраняет изменённый объект."""


class Reader[E, K](ABC):
    """Читает один объект аккаунта по его идентификатору."""

    @abstractmethod
    async def get(self, user_id: UserId, key: K) -> E | None:
        """Возвращает объект или None, если у аккаунта его нет."""


class Deleter[K](ABC):
    """Удаляет один объект аккаунта."""

    @abstractmethod
    async def delete(self, user_id: UserId, key: K) -> bool:
        """Удаляет объект, возвращая True, если он был."""


class ListAll[E](ABC):
    """Читает все объекты одного аккаунта."""

    @abstractmethod
    async def list_all(self, user_id: UserId) -> Sequence[E]:
        """Возвращает все объекты аккаунта."""


class Loader[E](ABC):
    """Читает единственную строку аккаунта."""

    @abstractmethod
    async def get(self, user_id: UserId) -> E | None:
        """Возвращает настройку аккаунта или None, если её никогда не сохраняли."""


class Saver[E](ABC):
    """Перезаписывает единственную строку аккаунта."""

    @abstractmethod
    async def save(self, entity: E) -> None:
        """Сохраняет настройку аккаунта."""


class CrudRepository[E, K](Creator[E], Reader[E, K], Updater[E], Deleter[K], ListAll[E]):
    """Репозиторий множества объектов одного аккаунта, поддерживающий весь набор операций."""
