"""Передача записанных фактов всем, кто на них подписан.

Два правила системы записаны реакциями, а не строками в конце каждого сценария: новому
аккаунту надо выдать дом, а ручное действие должно на время отодвинуть автоматику. Оба
выражены объектами, которые берут факты и что-то с ними делают, а этот раздатчик —
единственное место, где известен список.

Живёт раздатчик в прикладном слое, потому что список — бизнес-решение: новый подписчик
это новое правило о том, что значит записанный факт, а не новая зависимость
инфраструктуры.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

import structlog

from backend.application.interface.services.domain_event_dispatcher import DomainEventDispatcher

log = structlog.get_logger("application.reactions")

Reaction = Callable[[tuple[object, ...]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ReactionDispatcher(DomainEventDispatcher):
    """Объявляет записанные факты каждому подписчику, по порядку.

    Attributes:
        reactions: Подписчики, которым отдают факты.
    """

    reactions: tuple[Reaction, ...]

    async def dispatch(self, events: Sequence[object]) -> None:
        """Объявляет факты, которые агрегат записал, пока менялся.

        Отказавшего подписчика записывают в журнал и пропускают: транзакция уже
        закоммичена, и остальным подписчикам всё равно надо узнать о случившемся.

        Args:
            events: Факты, записанные с прошлого раза.
        """
        recorded = tuple(events)
        if not recorded:
            return
        for reaction in self.reactions:
            try:
                await reaction(recorded)
            except Exception as error:
                log.error(
                    "reaction.failed",
                    reaction=getattr(reaction, "__qualname__", type(reaction).__name__),
                    events=len(recorded),
                    error=str(error),
                )
