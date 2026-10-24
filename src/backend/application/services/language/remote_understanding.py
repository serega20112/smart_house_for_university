"""Составной конвейер: сперва спрашивают модель, потом местный словарь.

Удалённая модель отвечает структурированной командой, и её ответ нужно перевести в
то же понимание, что даёт местный конвейер, — с намерением из словаря и типизированными
значениями домена. Модель недоступна или молчит — дом не остаётся без понимания:
отказ записывается в журнал и предложение идёт местным путём.
"""

from __future__ import annotations

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.remote_answer import RemoteAnswer
from backend.application.errors import RemoteUnderstandingUnavailable
from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.interfaces.services.language.remote_understanding import (
    RemoteUnderstanding,
)
from backend.application.services.language.intents import intent_of
from backend.domain.exceptions import DomainError
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


class RemoteFirstUnderstanding(CommandUnderstandingPort):
    """Сначала спрашивает удалённую модель, потом местный конвейер.

    Attributes:
        remote: Клиент машины, крутящей модели, или None, когда развёртывание её
            не имеет.
        local: Конвейер, используемый всякий раз, когда у удалённой модели ответа нет.
    """

    def __init__(self, remote: RemoteUnderstanding | None, local: CommandUnderstandingPort) -> None:
        """Инициализирует составной интерфейс."""
        self._remote = remote
        self._local = local

    async def understand(self, text: str) -> CommandUnderstanding:
        """Толкует предложение.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            CommandUnderstanding: То, что из него сделал конвейер.
        """
        answer = await self._remote_answer(text)
        if answer is None:
            return await self._local.understand(text)
        return understanding_of(answer)

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Сообщает, можно ли выполненное понимание пускать в дело.

        Порог остаётся у местного конвейера: удалённая модель отвечает своей
        уверенностью, а решение о том, какая уверенность достаточна для этого дома,
        задаёт развёртывание один раз.

        Args:
            understanding: Результат конвейера.

        Returns:
            bool: True, когда команде можно идти дальше.
        """
        return await self._local.is_confident_enough(understanding)

    async def _remote_answer(self, text: str) -> RemoteAnswer | None:
        """Спрашивает модель; её отказ не превращается в аварию дома.

        Недоступная модель означает только одно: это предложение разберёт местный
        конвейер, поэтому отказ возвращается отсутствием ответа, а не исключением.

        Args:
            text: Предложение таким, каким его получил интерфейс.

        Returns:
            RemoteAnswer | None: Ответ модели либо None, когда её нет или она
            не смогла ответить.
        """
        if self._remote is None:
            return None
        try:
            return await self._remote.ask(text)
        except RemoteUnderstandingUnavailable:
            return None


def understanding_of(answer: RemoteAnswer) -> CommandUnderstanding:
    """Переводит ответ модели в понимание предложения.

    Args:
        answer: Структурированная команда из ответа модели.

    Returns:
        CommandUnderstanding: Понимание, в котором намерение может отсутствовать.
    """
    temperature = answer.temperature
    return CommandUnderstanding(
        intent=intent_of(answer.intent_name),
        device_name=answer.device_name,
        device_kinds=frozenset(_kinds_of(answer.device_kinds)),
        capability=_capability_of(answer.capability),
        temperature=None if temperature is None else Temperature(temperature),
        humidity=answer.humidity,
        delay_minutes=answer.delay_minutes,
        target=answer.target,
        confidence=answer.confidence,
    )


def _kinds_of(names: tuple[str, ...]) -> frozenset[DeviceKind]:
    found: set[DeviceKind] = set()
    for name in names:
        try:
            found.add(DeviceKind.parse(name))
        except DomainError:
            continue
    return frozenset(found)


def _capability_of(name: str | None) -> Capability | None:
    if name is None:
        return None
    try:
        return Capability.parse(name)
    except DomainError:
        return None
