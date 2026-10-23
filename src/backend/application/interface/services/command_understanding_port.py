"""Понимание свободной формулировки команды.

Приложение объявляет, чего оно ждёт от понимания: намерение, названные человеком
параметры и уверенность конвейера. Всё остальное — классификатор, векторы, порог
сходства и словарь любого языка — детали адаптера, который закрывает этот порт.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.application.dto.language.command_understanding import CommandUnderstanding


class CommandUnderstandingPort(ABC):
    """Превращает свободное предложение в структурированную команду."""

    @abstractmethod
    async def understand(self, text: str) -> CommandUnderstanding:
        """Разбирает сказанную или написанную фразу."""

    @abstractmethod
    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Можно ли выполнять то, что понял конвейер.

        Порог знает адаптер, которому понятно, насколько хорош его
        классификатор, поэтому приложение не держит число, осмысленное только для
        одной реализации.
        """
