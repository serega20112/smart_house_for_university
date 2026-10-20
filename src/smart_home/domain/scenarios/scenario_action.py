"""One action inside a timed scenario."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home.domain.climate.temperature import Temperature
from smart_home.domain.devices.capability import Capability


@dataclass(frozen=True, slots=True)
class ScenarioAction:
    """A capability a scenario asks for once it starts.

    The action names a capability and an optional target rather than a relay
    channel, because the device is chosen when the action runs: the wiring of a
    home may change while the scenario waits.

    Args:
        capability: Capability to perform.
        target_temperature: Temperature the action aims for, or None when the
            action only switches something.

    Returns:
        None.
    """

    capability: Capability
    target_temperature: Temperature | None = None

    @property
    def has_goal(self) -> bool:
        """Return whether the action can be judged as reached.

        Returns:
            bool: True when a target temperature was requested.
        """
        return self.target_temperature is not None
