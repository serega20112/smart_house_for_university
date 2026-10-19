"""Contracts of the home snapshot and of the free form command."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.application.dto.automation import AutomationView
from backend.application.dto.device import DeviceView
from backend.application.dto.scenario import ScenarioView
from backend.application.ports.language import Intent


@dataclass(frozen=True, slots=True)
class ReadingView:
    """Climate values as the interface needs them.

    Args:
        temperature: Measured temperature or None.
        humidity: Measured relative humidity or None.

    Returns:
        None.
    """

    temperature: float | None = None
    humidity: float | None = None


@dataclass(frozen=True, slots=True)
class HomeSnapshotView:
    """Everything one screen of the interface has to render.

    The volatile part is read once and the stored part is read once, so the numbers
    on the screen belong close enough together to be trusted instead of arriving
    from two sources a moment apart.

    Args:
        reading: Climate values right now.
        board_online: Whether any board of the account is connected.
        automation_suspended: Whether manual control is holding automation back.
        devices: Devices with their current status.
        automation: Automation configuration.
        active_scenarios: Scenarios that still outrank automation.

    Returns:
        None.
    """

    reading: ReadingView
    board_online: bool
    automation_suspended: bool
    devices: tuple[DeviceView, ...]
    automation: AutomationView
    active_scenarios: tuple[ScenarioView, ...]


@dataclass(frozen=True, slots=True)
class SubmitCommand:
    """A free form sentence submitted by a person.

    Args:
        text: The sentence as typed or as transcribed.

    Returns:
        None.
    """

    text: str


@dataclass(frozen=True, slots=True)
class CommandReply:
    """What carrying a command out produced.

    A refused command is not a value carrying a status inside it: the use case
    raises, and the interface catches. What stays here is the answer itself.

    Args:
        intent: Intent that was carried out, or None when the sentence could not be
            understood at all.
        answer: Text describing what happened.
        details: Machine readable extras, such as the devices that changed.

    Returns:
        None.
    """

    intent: Intent | None
    answer: str
    details: dict[str, object] = field(default_factory=dict)
