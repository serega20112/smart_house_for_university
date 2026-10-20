"""Domain failures.

Every error a business rule can refuse is declared here and nowhere else, so a
reader can audit the whole vocabulary of refusals of the model in one file.

The list contains invariant violations only: values the model refuses to hold and
transitions it refuses to make. Failures that come from the outside world belong
to the layer that meets that world: a login that does not match a stored hash is
an application failure, and a duplicate login is a storage constraint.

Each error carries the context needed to describe the refusal to a person, and
the presentation layer maps the type onto an HTTP code, never the other way
around.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class of every refusal produced by a business rule."""


class MalformedIdentifierError(DomainError):
    """A textual identifier cannot be read as the UUID it claims to be.

    Args:
        kind: Name of the identifier type.
        raw: Value that could not be parsed.

    Returns:
        None.
    """

    def __init__(self, kind: str, raw: Any) -> None:
        super().__init__(f"{kind} is not a valid identifier: {raw!r}")
        self.kind = kind
        self.raw = raw


class InvalidEmailError(DomainError):
    """A login does not look like an email address.

    Args:
        reason: Why the value was refused.

    Returns:
        None.
    """

    def __init__(self, reason: str = "value is not a valid email address") -> None:
        super().__init__(f"Email {reason}")
        self.reason = reason


class InvalidDisplayNameError(DomainError):
    """A display name is empty or too long to render.

    Args:
        reason: Why the value was refused.

    Returns:
        None.
    """

    def __init__(self, reason: str = "value is empty or too long") -> None:
        super().__init__(f"Display name {reason}")
        self.reason = reason


class WeakPasswordError(DomainError):
    """A password does not satisfy the minimal length the model accepts.

    Args:
        minimum: Minimal accepted length.

    Returns:
        None.
    """

    def __init__(self, minimum: int) -> None:
        super().__init__(f"Password must be at least {minimum} characters long")
        self.minimum = minimum


class InvalidTemperatureError(DomainError):
    """A temperature lies outside the physically possible range.

    Args:
        celsius: Refused value.

    Returns:
        None.
    """

    def __init__(self, celsius: float) -> None:
        super().__init__(f"temperature out of range: {celsius}")
        self.celsius = celsius


class InvalidHumidityError(DomainError):
    """A relative humidity lies outside the zero to one hundred range.

    Args:
        percent: Refused value.

    Returns:
        None.
    """

    def __init__(self, percent: float) -> None:
        super().__init__(f"humidity out of range: {percent}")
        self.percent = percent


class InvalidToleranceError(DomainError):
    """A hysteresis tolerance is negative, which has no meaning as a band.

    Args:
        tolerance: Refused value.

    Returns:
        None.
    """

    def __init__(self, tolerance: float) -> None:
        super().__init__(f"tolerance must not be negative: {tolerance}")
        self.tolerance = tolerance


class InvalidDeviceNameError(DomainError):
    """A device name is empty or too long to render.

    Args:
        reason: Why the value was refused.

    Returns:
        None.
    """

    def __init__(self, reason: str = "value is empty or too long") -> None:
        super().__init__(f"Device name {reason}")
        self.reason = reason


class InvalidRelayChannelError(DomainError):
    """A relay channel number does not exist on the hardware.

    Args:
        channel: Refused channel number.
        limit: Highest channel the hardware has.

    Returns:
        None.
    """

    def __init__(self, channel: int, limit: int) -> None:
        super().__init__(f"relay channel {channel} is outside 1..{limit}")
        self.channel = channel
        self.limit = limit


class ChannelConflictError(DomainError):
    """A physical channel is already wired to another device of the same account.

    Args:
        channel: Physical relay channel.

    Returns:
        None.
    """

    def __init__(self, channel: int) -> None:
        super().__init__(f"relay channel {channel} is already wired to another device")
        self.channel = channel


class UnsupportedCapabilityError(DomainError):
    """A device cannot perform the requested capability.

    Args:
        device_name: Name of the device.
        capability: Requested capability.

    Returns:
        None.
    """

    def __init__(self, device_name: str, capability: str) -> None:
        super().__init__(f"device {device_name!r} does not support {capability}")
        self.device_name = device_name
        self.capability = capability


class NoDeviceForCapabilityError(DomainError):
    """No configured device is able to satisfy a requested capability.

    Args:
        capability: Requested capability.

    Returns:
        None.
    """

    def __init__(self, capability: str) -> None:
        super().__init__(f"no device in this home supports {capability}")
        self.capability = capability


class ScenarioAlreadyFinishedError(DomainError):
    """A scenario that reached a final stage cannot be cancelled or completed again.

    Args:
        scenario_id: Identifier of the scenario.
        status: Stage the scenario already reached.

    Returns:
        None.
    """

    def __init__(self, scenario_id: str, status: str) -> None:
        super().__init__(f"scenario {scenario_id} is already {status}")
        self.scenario_id = scenario_id
        self.status = status


class IllegalScenarioTransitionError(DomainError):
    """A scenario was asked to move between two stages that cannot follow.

    Args:
        scenario_id: Identifier of the scenario.
        current: Stage the scenario is in.
        requested: Stage the caller asked for.

    Returns:
        None.
    """

    def __init__(self, scenario_id: str, current: str, requested: str) -> None:
        super().__init__(f"scenario {scenario_id} cannot go from {current} to {requested}")
        self.scenario_id = scenario_id
        self.current = current
        self.requested = requested


class InvalidBoardNameError(DomainError):
    """A board name is empty or too long to render.

    Args:
        reason: Why the value was refused.

    Returns:
        None.
    """

    def __init__(self, reason: str = "value is empty or too long") -> None:
        super().__init__(f"Board name {reason}")
        self.reason = reason


class InvalidPairingKeyError(DomainError):
    """A pairing key is empty or malformed.

    Args:
        reason: Why the value was refused.

    Returns:
        None.
    """

    def __init__(self, reason: str = "value is empty or malformed") -> None:
        super().__init__(f"Pairing key {reason}")
        self.reason = reason


class InvalidNetworkProfileError(DomainError):
    """The network of a board cannot be used as it was given.

    Args:
        reason: Why the values were refused.

    Returns:
        None.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"Network profile {reason}")
        self.reason = reason


class ClaimExpiredError(DomainError):
    """The window in which a board could be taken has closed.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        super().__init__(
            "this board announcement is no longer valid, ask the board to announce again"
        )


class ClaimAlreadyTakenError(DomainError):
    """Another account took the board first.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        super().__init__("this board is already owned by another account")


class InvalidDashboardLayoutError(DomainError):
    """A dashboard layout breaks an invariant of the layout aggregate.

    Args:
        reason: Why the layout was refused.

    Returns:
        None.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid dashboard layout: {reason}")
        self.reason = reason


class DashboardAccessDeniedError(DomainError):
    """A widget points at a device the account does not own.

    Args:
        device_id: Device the widget referenced.

    Returns:
        None.
    """

    def __init__(self, device_id: str) -> None:
        super().__init__(f"device {device_id} does not belong to this account")
        self.device_id = device_id
