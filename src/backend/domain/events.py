"""Domain events.

An entity that changes something worth telling about records the fact instead of
calling a notifier. The application layer drains those records after the
transaction commits and hands them to whatever is subscribed, which keeps the
model free of messaging infrastructure and of any knowledge about who listens.

An event is a plain immutable statement of something that already happened. It
carries no timestamp and no delivery information: the moment is stamped by the
publisher, which is the only component that knows when the fact became visible
outside the transaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain.identifiers import DeviceId, EspDeviceId, ScenarioId, UserId


@dataclass(frozen=True, slots=True)
class UserRegistered:
    """A new account exists and its home has to be provisioned.

    Args:
        user_id: Identifier of the new account.

    Returns:
        None.
    """

    user_id: UserId


@dataclass(frozen=True, slots=True)
class DeviceConfigured:
    """The configuration of a logical device changed.

    Args:
        user_id: Owner of the device.
        device_id: Identifier of the changed device.

    Returns:
        None.
    """

    user_id: UserId
    device_id: DeviceId


@dataclass(frozen=True, slots=True)
class DeviceCapabilityApplied:
    """A capability reached the hardware on behalf of an account.

    This is the single place the rule "a manual action suspends automation for a
    while" is written down, instead of a line repeated at the end of every use
    case that switches something.

    Args:
        user_id: Owner of the device.
        device_id: Identifier of the device.
        device_name: Name shown to the user.
        channel: Physical relay channel that was switched.
        capability: Capability that was performed.
        manual: Whether a person asked for it, as opposed to automation or a
            scenario.

    Returns:
        None.
    """

    user_id: UserId
    device_id: DeviceId
    device_name: str
    channel: int
    capability: str
    manual: bool


@dataclass(frozen=True, slots=True)
class AutomationSettingsChanged:
    """The automation configuration of an account changed.

    Args:
        user_id: Owner of the configuration.

    Returns:
        None.
    """

    user_id: UserId


@dataclass(frozen=True, slots=True)
class ScenarioScheduled:
    """A scenario was stored and waits for its start moment.

    Args:
        user_id: Owner of the scenario.
        scenario_id: Identifier of the scenario.

    Returns:
        None.
    """

    user_id: UserId
    scenario_id: ScenarioId


@dataclass(frozen=True, slots=True)
class ScenarioStarted:
    """A scenario began acting on the home.

    Args:
        user_id: Owner of the scenario.
        scenario_id: Identifier of the scenario.

    Returns:
        None.
    """

    user_id: UserId
    scenario_id: ScenarioId


@dataclass(frozen=True, slots=True)
class ScenarioFinished:
    """A scenario reached a final stage.

    Args:
        user_id: Owner of the scenario.
        scenario_id: Identifier of the scenario.
        status: Stage the scenario reached.
        reason: Why it reached that stage.

    Returns:
        None.
    """

    user_id: UserId
    scenario_id: ScenarioId
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class BoardPaired:
    """A board became owned by an account.

    Args:
        user_id: Owner of the board.
        board_id: Identifier of the board.

    Returns:
        None.
    """

    user_id: UserId
    board_id: EspDeviceId


@dataclass(frozen=True, slots=True)
class BoardAnnouncementPublished:
    """A board nobody owns yet is asking to be taken.

    Args:
        label: Short code the interface shows next to the board.

    Returns:
        None.
    """

    label: str = field(compare=False)
