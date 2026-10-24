"""Logical device of a smart home.

A physical relay is not a device. The mapping "device -- channel" is stored
here, so a person decides what a channel means without touching the firmware;
therefore any automation rule speaks of capabilities, not relay numbers.

The entity owns its rules: it knows which capability it can perform,
when it participates in automation and how to change its settings. Entity fields
are not assigned from outside.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from backend.domain.events import DeviceCapabilityApplied, DeviceConfigured
from backend.domain.exceptions import InvalidDeviceNameError, UnsupportedCapabilityError
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_channel import RelayChannel

MAX_NAME_LENGTH = 120


@dataclass
class Device:
    """Logical smart home device.

    Attributes:
        id: Identifier issued at creation.
        user_id: Device owner.
        name: Name shown to the person.
        kind: What the device is for.
        channel: Relay channel the device is connected to.
        board_id: Board the channel is on, or None when the board is not yet
            registered (single-board home, where the board is allowed by the presence registry).
        capabilities: Actions the device can perform.
        enabled: Whether the device can be controlled at all.
        automation_enabled: Whether the device participates in automation.
        version: Version counter.
        _events: Internal event log.

    Raises:
        InvalidDeviceNameError: When the name is empty or too long.
    """

    id: DeviceId
    user_id: UserId
    name: str
    kind: DeviceKind
    channel: RelayChannel
    board_id: EspDeviceId | None = None
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    enabled: bool = True
    automation_enabled: bool = True
    version: int = 0
    _events: list[DeviceConfigured | DeviceCapabilityApplied] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Validate the device name.

        Raises:
            InvalidDeviceNameError: When the name is empty or too long.
        """
        trimmed = self.name.strip()
        if not trimmed or len(trimmed) > MAX_NAME_LENGTH:
            raise InvalidDeviceNameError()
        self.name = trimmed

    def supports(self, capability: Capability) -> bool:
        """Report whether the device can perform a capability.

        Args:
            capability: The capability to check.

        Returns:
            bool: True when the device is capable of this capability.
        """
        return capability in self.capabilities

    def require_capability(self, capability: Capability) -> None:
        """Reject a capability the device cannot execute.

        Args:
            capability: The requested capability.

        Raises:
            UnsupportedCapabilityError: When the capability is not supported.
        """
        if not self.supports(capability):
            raise UnsupportedCapabilityError(self.name, capability.value)

    @property
    def is_controllable(self) -> bool:
        """Reports whether this device can be controlled at all."""
        return self.enabled

    @property
    def takes_part_in_automation(self) -> bool:
        """Reports whether this device is allowed in automation."""
        return self.enabled and self.automation_enabled

    def drive(self, capability: Capability, source_is_manual: bool) -> DeviceStatus:
        """Records that a capability was performed on this device.

        The entity does not talk to hardware: it validates the request, stores the fact and
        reports what the device will become afterwards.

        Args:
            capability: Performed capability.
            source_is_manual: Whether a person requested it or automation/scenario.

        Returns:
            DeviceStatus: State the device reached.

        Raises:
            UnsupportedCapabilityError: When the capability is not supported.
        """
        self.require_capability(capability)
        result = DeviceStatus.after(capability)
        self._events.append(
            DeviceCapabilityApplied(
                user_id=self.user_id,
                device_id=self.id,
                device_name=self.name,
                channel=int(self.channel),
                capability=capability.value,
                manual=source_is_manual,
            )
        )
        return result

    def record_change(self) -> None:
        """Records that this device configuration changed."""
        self._events.append(DeviceConfigured(user_id=self.user_id, device_id=self.id))

    def pull_events(self) -> tuple[DeviceConfigured | DeviceCapabilityApplied, ...]:
        """Returns recorded facts and forgets them.

        Returns:
            tuple[DeviceConfigured | DeviceCapabilityApplied, ...]: Facts from
            the previous access.
        """
        recorded = tuple(self._events)
        self._events.clear()
        return recorded

    def reconfigure(
        self,
        *,
        name: str | None = None,
        kind: DeviceKind | None = None,
        channel: RelayChannel | None = None,
        capabilities: frozenset[Capability] | None = None,
        enabled: bool | None = None,
        automation_enabled: bool | None = None,
    ) -> None:
        """Apply partial configuration change.

        Args:
            name: New name or None to keep current.
            kind: New kind or None to keep current.
            channel: New relay channel or None to keep current.
            capabilities: New capabilities or None to keep current.
            enabled: New enabled flag or None to keep current.
            automation_enabled: New automation enabled flag or None to keep current.

        Raises:
            InvalidDeviceNameError: When the new name is empty or too long.
        """
        if name is not None:
            trimmed = name.strip()
            if not trimmed or len(trimmed) > MAX_NAME_LENGTH:
                raise InvalidDeviceNameError()
            self.name = trimmed
        if kind is not None:
            self.kind = kind
        if channel is not None:
            self.channel = channel
        if capabilities is not None:
            self.capabilities = frozenset(capabilities)
        if enabled is not None:
            self.enabled = enabled
        if automation_enabled is not None:
            self.automation_enabled = automation_enabled

    @classmethod
    def create(
        cls,
        user_id: UserId,
        name: str,
        kind: DeviceKind,
        channel: RelayChannel,
        capabilities: frozenset[Capability],
        *,
        board_id: EspDeviceId | None = None,
        enabled: bool = True,
        automation_enabled: bool = True,
    ) -> Self:
        """Create a new device with a generated identifier.

        Args:
            user_id: Device owner.
            name: Name shown to the person.
            kind: What the device is for.
            channel: Relay channel the device is connected to.
            capabilities: Actions the device can perform.
            board_id: Board the channel is on, or None for single-board home.
            enabled: Whether the device can be controlled at all.
            automation_enabled: Whether the device participates in automation.

        Returns:
            Self: The created device.
        """
        return cls(
            id=DeviceId.generate(),
            user_id=user_id,
            name=name,
            kind=kind,
            channel=channel,
            board_id=board_id,
            capabilities=capabilities,
            enabled=enabled,
            automation_enabled=automation_enabled,
        )
