"""Logical device of the smart home.

A physical relay is not a device. The mapping device to channel is stored here,
which lets the user decide what a channel means without touching the firmware, and
it is the reason every automation rule speaks about capabilities instead of relay
numbers.

The entity owns its own rules: it knows whether it can perform a capability, when
it takes part in automation and how to change its configuration. Callers never
assign to its fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device_kind import DeviceKind
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.devices.relay_channel import RelayChannel
from smart_home.domain.events import DeviceCapabilityApplied, DeviceConfigured
from smart_home.domain.exceptions import InvalidDeviceNameError, UnsupportedCapabilityError
from smart_home.domain.identifiers import DeviceId, UserId

MAX_NAME_LENGTH = 120


@dataclass
class Device:
    """A device the user configured on a relay channel of their board.

    Args:
        id: Identifier assigned at creation.
        user_id: Owner of the device.
        name: Name shown to the user.
        kind: What the device is for.
        channel: Relay channel the device is wired to.
        capabilities: Actions the device is able to perform.
        enabled: Whether the device may be controlled at all.
        automation_enabled: Whether the device takes part in automation.

    Returns:
        None.

    Raises:
        InvalidDeviceNameError: When the name is empty or too long.
    """

    id: DeviceId
    user_id: UserId
    name: str
    kind: DeviceKind
    channel: RelayChannel
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    enabled: bool = True
    automation_enabled: bool = True
    version: int = 0
    _events: list[DeviceConfigured | DeviceCapabilityApplied] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Validate the name of the device.

        Returns:
            None.

        Raises:
            InvalidDeviceNameError: When the name is empty or too long.
        """
        trimmed = self.name.strip()
        if not trimmed or len(trimmed) > MAX_NAME_LENGTH:
            raise InvalidDeviceNameError()
        self.name = trimmed

    def supports(self, capability: Capability) -> bool:
        """Return whether the device is able to perform a capability.

        Args:
            capability: Capability to check.

        Returns:
            bool: True when supported.
        """
        return capability in self.capabilities

    def require_capability(self, capability: Capability) -> None:
        """Refuse a capability the device cannot perform.

        Args:
            capability: Required capability.

        Returns:
            None.

        Raises:
            UnsupportedCapabilityError: When the capability is not supported.
        """
        if not self.supports(capability):
            raise UnsupportedCapabilityError(self.name, capability.value)

    @property
    def is_controllable(self) -> bool:
        """Return whether the device may be driven by anything at all.

        Returns:
            bool: True when the device is enabled.
        """
        return self.enabled

    @property
    def takes_part_in_automation(self) -> bool:
        """Return whether automation is allowed to drive this device.

        Returns:
            bool: True when the device is enabled and opted in.
        """
        return self.enabled and self.automation_enabled

    def drive(self, capability: Capability, source_is_manual: bool) -> DeviceStatus:
        """Record that a capability was performed on this device.

        The entity does not talk to the hardware; it validates the request, keeps
        the fact and states what the device looks like afterwards.

        Args:
            capability: Capability that was performed.
            source_is_manual: Whether a person asked for it.

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
        """Record that the configuration of this device changed.

        Returns:
            None.
        """
        self._events.append(DeviceConfigured(user_id=self.user_id, device_id=self.id))

    def pull_events(self) -> tuple[DeviceConfigured | DeviceCapabilityApplied, ...]:
        """Return the recorded facts and forget them.

        Returns:
            tuple[DeviceConfigured | DeviceCapabilityApplied, ...]: Facts recorded
            since the last call.
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
        """Apply a partial change to the configuration.

        Args:
            name: New name or None to keep the current one.
            kind: New kind or None to keep the current one.
            channel: New relay channel or None to keep the current one.
            capabilities: New capabilities or None to keep the current ones.
            enabled: New availability flag or None to keep the current one.
            automation_enabled: New automation flag or None to keep the current one.

        Returns:
            None.

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
        enabled: bool = True,
        automation_enabled: bool = True,
    ) -> Self:
        """Build a new device with an identifier of its own.

        Args:
            user_id: Owner of the device.
            name: Name shown to the user.
            kind: What the device is for.
            channel: Relay channel the device is wired to.
            capabilities: Actions the device is able to perform.
            enabled: Whether the device may be controlled at all.
            automation_enabled: Whether the device takes part in automation.

        Returns:
            Self: Created device.
        """
        return cls(
            id=DeviceId.generate(),
            user_id=user_id,
            name=name,
            kind=kind,
            channel=channel,
            capabilities=capabilities,
            enabled=enabled,
            automation_enabled=automation_enabled,
        )
