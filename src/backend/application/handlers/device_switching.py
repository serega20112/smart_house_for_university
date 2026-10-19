"""Handlers of the intents that switch devices."""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.dto.home import CommandReply
from backend.application.errors import CommandNotUnderstoodError
from backend.application.ports.language import ClarificationReason, CommandUnderstanding, Intent
from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.domain.devices.capability import Capability
from backend.domain.devices.device import Device
from backend.domain.identifiers import UserId
from backend.domain.services.device_selector import DeviceSelector


class SwitchDeviceHandler:
    """Answers "turn this on" and "turn that off"."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        selector: DeviceSelector,
        on_capability: Capability,
        off_capability: Capability,
        energized: bool,
    ) -> None:
        """Initialize the handler.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            selector: Resolves the device a reference points at.
            on_capability: Capability meaning "switch on".
            off_capability: Capability meaning "switch off".
            energized: Whether this handler switches on or off.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control
        self._selector = selector
        self._on = on_capability
        self._off = off_capability
        self._energized = energized

    @property
    def intent(self) -> Intent:
        """Return the intent this handler serves.

        Returns:
            Intent: Intent of the handler.
        """
        return Intent.SWITCH_DEVICE

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Switch the device the sentence points at.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: What carrying the command out produced.

        Raises:
            CommandNotUnderstoodError: When the sentence names no known device.
        """
        devices = await self._devices(user_id)
        device = self._resolve(devices, parsed)
        if device is None:
            raise CommandNotUnderstoodError(
                ClarificationReason.UNKNOWN_DEVICE, device=parsed.device_name
            )
        capability = self._on if self._energized else self._off
        view = await self._control.apply_to_device(user_id, device.id, capability)
        return CommandReply(
            intent=self.intent,
            answer="",
            details={"device": view.name, "status": view.status.value},
        )

    async def _devices(self, user_id: UserId) -> Sequence[Device]:
        async with self._home_uow() as uow:
            return list(await uow.devices.list_all(user_id))

    def _resolve(
        self, devices: Sequence[Device], parsed: CommandUnderstanding
    ) -> Device | None:
        if parsed.device_name:
            return self._selector.by_name(devices, parsed.device_name)
        if parsed.device_kinds:
            candidates = self._selector.of_kind(devices, parsed.device_kinds)
            return candidates[0] if candidates else None
        return None


class SwitchAllHandler:
    """Answers "turn everything on" and "turn everything off"."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        capability: Capability,
        energized: bool,
    ) -> None:
        """Initialize the handler.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            capability: Capability meaning "switch on".
            energized: Whether this handler switches on or off.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control
        self._capability = capability
        self._energized = energized

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Switch every device that supports the capability.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: Devices that changed.
        """
        async with self._home_uow() as uow:
            devices = list(await uow.devices.list_all(user_id))
        capability = self._capability if self._energized else Capability.OFF
        report = await self._control.apply_to_all(user_id, devices, capability)
        return CommandReply(
            intent=Intent.SWITCH_ALL,
            answer="",
            details={"devices": [view.name for view in report.devices]},
        )
