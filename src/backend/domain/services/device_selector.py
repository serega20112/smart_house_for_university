"""Choosing the device a command is meant for.

Two questions are answered here: which device can perform a capability, and which
device a free form reference points at. Both are decisions of the model, so they
live in a domain service rather than in a module of functions a caller has to
remember to use.

What this service deliberately does not know is any word in any language. Reading
"кондиционер" as a hint about the air conditioner belongs to the language
pipeline, which may answer in any language at all; the model only compares names.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from backend.domain.climate.automation_settings import AutomationSettings
from backend.domain.devices.capability import Capability
from backend.domain.devices.device import Device
from backend.domain.devices.device_kind import DeviceKind
from backend.domain.identifiers import DeviceId


class DeviceSelector:
    """Resolves devices by capability, by name and by automation participation."""

    def first_supporting(
        self,
        devices: Iterable[Device],
        capability: Capability,
        settings: AutomationSettings | None = None,
        *,
        automation_only: bool = False,
    ) -> Device | None:
        """Return the first device able to perform a capability.

        Args:
            devices: Candidate devices.
            capability: Required capability.
            settings: Automation settings used to filter participants.
            automation_only: Whether only automation participants are considered.

        Returns:
            Device | None: Matching device, or None when there is none.
        """
        for device in devices:
            if not device.is_controllable:
                continue
            if automation_only and not self._participates(device, settings):
                continue
            if device.supports(capability):
                return device
        return None

    def all_supporting(
        self, devices: Iterable[Device], capability: Capability
    ) -> list[Device]:
        """Return every device able to perform a capability.

        Args:
            devices: Candidate devices.
            capability: Required capability.

        Returns:
            list[Device]: Matching devices in the order they were given.
        """
        return [
            device
            for device in devices
            if device.is_controllable and device.supports(capability)
        ]

    def by_name(self, devices: Sequence[Device], reference: str) -> Device | None:
        """Return the device a free form reference points at by name.

        An exact name always wins. A partial name is accepted next, preferring the
        shortest match, and finally a device whose own name appears inside the
        reference, which is what makes "включи свет на кухне" reach the lamp even
        though the sentence carries more than the name.

        Args:
            devices: Candidate devices.
            reference: Device name fragment taken from the user command.

        Returns:
            Device | None: Matching device, or None when the name is unknown.
        """
        needle = reference.strip().lower()
        if not needle:
            return None
        exact = [device for device in devices if device.name.lower() == needle]
        if exact:
            return exact[0]
        partial = [device for device in devices if needle in device.name.lower()]
        if partial:
            return min(partial, key=lambda device: len(device.name))
        contained = [device for device in devices if device.name.lower() in needle]
        if contained:
            return max(contained, key=lambda device: len(device.name))
        return None

    def of_kind(
        self, devices: Iterable[Device], kinds: frozenset[DeviceKind]
    ) -> list[Device]:
        """Return every controllable device of the given kinds.

        This is how a language hint reaches the model: the pipeline decides which
        kinds a phrase might mean, and the model decides which of those devices
        actually exist.

        Args:
            devices: Candidate devices.
            kinds: Kinds the phrase could be about.

        Returns:
            list[Device]: Matching devices.
        """
        return [
            device
            for device in devices
            if device.is_controllable and device.kind in kinds
        ]

    def owned_ids(self, devices: Iterable[Device]) -> frozenset[DeviceId]:
        """Return the identifiers of every device an account owns.

        Args:
            devices: Devices of the account.

        Returns:
            frozenset[DeviceId]: Owned identifiers.
        """
        return frozenset(device.id for device in devices)

    def _participates(self, device: Device, settings: AutomationSettings | None) -> bool:
        if not device.takes_part_in_automation:
            return False
        if settings is None:
            return True
        return settings.device_participates(device.id)
