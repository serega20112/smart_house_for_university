"""Понимание предложения словарём, а смыслового конвейера — только для непонятого.

Смысловой конвейер никуда не делся: он остаётся тем, что понимает непривычный оборот.
Но платить за него на каждой фразе не нужно, а на развёртывании без необязательной
зависимости модели — и нельзя. Поэтому словарь идёт первым, а вектор спрашивают ровно
один раз и ровно о тех словах, которые он не узнал.
"""

from __future__ import annotations

from typing import Final

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.services.language.lexicon import intent_in
from backend.application.services.language.parser import SentenceParser

FULL_CONFIDENCE: Final = 1.0


class LexiconUnderstanding(CommandUnderstandingPort):
    """Толкует предложение теми словами, которые знает словарь.

    Attributes:
        parser: Читатель параметров предложения.
    """

    def __init__(self, parser: SentenceParser) -> None:
        """Инициализирует конвейер."""
        self._parser = parser

    async def understand(self, text: str) -> CommandUnderstanding:
        """Толкует предложение.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            CommandUnderstanding: Названные параметры и узнанное намерение. Уверенность
            полная, потому что словарь сравнивает слова: совпадение не бывает частичным.
            Намерение равно None, когда словарь не узнал ничего.
        """
        facts = self._parser.parse(text)
        intent = intent_in(text, facts)
        return CommandUnderstanding(
            intent=intent,
            device_name=facts.device_name,
            device_kinds=facts.device_kinds,
            capability=facts.capability,
            temperature=facts.temperature,
            humidity=facts.humidity,
            delay_minutes=facts.delay_minutes,
            target=facts.target,
            confidence=0.0 if intent is None else FULL_CONFIDENCE,
        )

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Сообщает, можно ли выполненное понимание пускать в дело.

        Args:
            understanding: Результат конвейера.

        Returns:
            bool: True, когда намерение узнано: словарю нечего уточнять порогом.
        """
        return understanding.intent is not None


class DictionaryFirstUnderstanding(CommandUnderstandingPort):
    """Спрашивает словарь, а смысловой конвейер — только о непонятом.

    Attributes:
        dictionary: Конвейер, узнающий знакомые слова.
        semantic: Конвейер, сравнивающий смыслы, когда слов не хватило.
    """

    def __init__(
        self, dictionary: CommandUnderstandingPort, semantic: CommandUnderstandingPort
    ) -> None:
        """Инициализирует составной конвейер."""
        self._dictionary = dictionary
        self._semantic = semantic

    async def understand(self, text: str) -> CommandUnderstanding:
        """Толкует предложение.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            CommandUnderstanding: Понимание словаря либо, когда тот промолчал,
            понимание смыслового конвейера.
        """
        understood = await self._dictionary.understand(text)
        if understood.intent is not None:
            return understood
        return await self._semantic.understand(text)

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Сообщает, можно ли выполненное понимание пускать в дело.

        Порог остаётся у смыслового конвейера: он один знает, насколько хорош его
        классификатор, а словарь узнаёт намерение целиком или не узнаёт вовсе.

        Args:
            understanding: Результат конвейера.

        Returns:
            bool: True, когда команде можно идти дальше.
        """
        if understanding.intent is None:
            return False
        return await self._semantic.is_confident_enough(understanding)
