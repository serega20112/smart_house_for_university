"""Reactions to the facts the model records.

The rules "a manual action holds automation back" and "a scenario that finished
puts the devices back" are written here as reactions to what an aggregate recorded,
not as lines at the end of every use case. A use case that switches a device
therefore does not have to remember any of this, and a new entry point into the
system inherits the behaviour for free.
"""

from __future__ import annotations

from backend.application.ports.services import Clock, HomeStateStore
from backend.domain.events import DeviceCapabilityApplied


class ManualOverrideReaction:
    """Holds automation back for a while after a person touched a device."""

    def __init__(
        self, state_store: HomeStateStore, clock: Clock, override_minutes: int
    ) -> None:
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
            event
            for event in events
            if isinstance(event, DeviceCapabilityApplied) and event.manual
        ]
        if not manual:
            return
        state = await self._state_store.load(manual[0].user_id)
        state.suspend_automation_for(self._clock.now(), self._override_minutes)
        await self._state_store.save(state)
