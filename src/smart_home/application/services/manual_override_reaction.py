"""Reactions to the facts the model records.

The rules "a manual action holds automation back" and "a scenario that finished
puts the devices back" are written here as reactions to what an aggregate recorded,
not as lines at the end of every use case. A use case that switches a device
therefore does not have to remember any of this, and a new entry point into the
system inherits the behaviour for free.
"""

from __future__ import annotations

from datetime import timedelta

from smart_home.application.ports.services import Clock, HomeStateStore
from smart_home.domain.events import DeviceCapabilityApplied
from smart_home.domain.identifiers import UserId


class ManualOverrideReaction:
    """Holds automation back for a while after a person touched a device."""

    def __init__(self, state_store: HomeStateStore, clock: Clock, override_minutes: int) -> None:
        """Initialize the reaction.

        Args:
            state_store: Durable home of the volatile state.
            clock: Source of the current time.
            override_minutes: How long a manual action holds automation back.

        Returns:
            None.
        """
        self._state_store = state_store
        self._clock = clock
        self._override_minutes = override_minutes

    async def __call__(self, events: tuple[object, ...]) -> None:
        """React to the recorded facts.

        Args:
            events: Facts recorded by an aggregate.

        Returns:
            None.
        """
        manual = [
            event for event in events if isinstance(event, DeviceCapabilityApplied) and event.manual
        ]
        if not manual:
            return
        by_home: dict[UserId, object] = {}
        for event in manual:
            by_home[event.user_id] = None
        for user_id in by_home:
            until = self._clock.now() + timedelta(minutes=self._override_minutes)
            await self._state_store.set_override_until(user_id, until)
