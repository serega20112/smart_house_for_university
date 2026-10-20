"""Handing recorded facts to everything that subscribed to them.

Two rules of the system are written as reactions rather than as lines at the end
of every use case: a new account has to be given a home, and a manual action has
to hold automation back for a while. Both are expressed by objects that take the
facts and do something with them, and this dispatcher is the single place that
knows the list.

It lives in the application layer because the list is a business decision: a new
subscriber is a new rule about what a recorded fact means, not a new dependency
of the infrastructure.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

import structlog

from smart_home.application.ports.events import DomainEventDispatcher

log = structlog.get_logger("application.reactions")

Reaction = Callable[[tuple[object, ...]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ReactionDispatcher(DomainEventDispatcher):
    """Announces recorded facts to every subscriber, in order.

    Args:
        reactions: Subscribers the facts are handed to.

    Returns:
        None.
    """

    reactions: tuple[Reaction, ...]

    async def dispatch(self, events: Sequence[object]) -> None:
        """Announce facts an aggregate recorded while it was changing.

        A subscriber that fails is reported and skipped: the transaction is
        already committed and the remaining subscribers still have to hear about
        what happened.

        Args:
            events: Facts recorded since the last dispatch.

        Returns:
            None.
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
