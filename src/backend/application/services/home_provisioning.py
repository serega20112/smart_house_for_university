"""Give a new account a home to live in.

This is a reaction to the fact an account recorded when it was created, not a step
of the registration use case. Registration knows how to create an account; what
that account should come with is a separate decision, and it changes without the
registration code being touched.
"""

from __future__ import annotations

from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.climate.automation_settings import AutomationSettings
from backend.domain.devices.capability import Capability
from backend.domain.devices.device import Device
from backend.domain.devices.device_kind import DeviceKind
from backend.domain.devices.relay_channel import RelayChannel
from backend.domain.events import UserRegistered
from backend.domain.identifiers import UserId
from backend.domain.personalization.dashboard_state import DashboardState
from backend.domain.personalization.user_preferences import UserPreferences


class StarterDevice:
    """Description of one device a new account starts with.

    Args:
        name: Name shown to the user.
        kind: What the device is for.
        channel: Relay channel the device is wired to.
        capabilities: Actions the device is able to perform.
        automation_enabled: Whether the device takes part in automation.

    Returns:
        None.
    """

    __slots__ = ("automation_enabled", "capabilities", "channel", "kind", "name")

    def __init__(
        self,
        name: str,
        kind: DeviceKind,
        channel: int,
        capabilities: frozenset[Capability],
        automation_enabled: bool,
    ) -> None:
        """Initialize the description.

        Args:
            name: Name shown to the user.
            kind: What the device is for.
            channel: Relay channel the device is wired to.
            capabilities: Actions the device is able to perform.
            automation_enabled: Whether the device takes part in automation.

        Returns:
            None.
        """
        self.name = name
        self.kind = kind
        self.channel = channel
        self.capabilities = capabilities
        self.automation_enabled = automation_enabled

    def build(self, user_id: UserId) -> Device:
        """Build the device itself.

        Args:
            user_id: Owner of the device.

        Returns:
            Device: Created device.
        """
        return Device.create(
            user_id=user_id,
            name=self.name,
            kind=self.kind,
            channel=RelayChannel(self.channel),
            capabilities=self.capabilities,
            automation_enabled=self.automation_enabled,
        )


SWITCHING = frozenset({Capability.ON, Capability.OFF})
CLIMATE = frozenset({Capability.OFF, Capability.COOL, Capability.HEAT})
HUMIDITY = frozenset({Capability.OFF, Capability.HUMIDIFY, Capability.DEHUMIDIFY})

STARTER_DEVICES: tuple[StarterDevice, ...] = (
    StarterDevice("Лампа", DeviceKind.LIGHT, 1, SWITCHING, False),
    StarterDevice("Увлажнитель", DeviceKind.HUMIDIFIER, 2, HUMIDITY, True),
    StarterDevice("Вентилятор", DeviceKind.FAN, 3, SWITCHING, True),
    StarterDevice("Обогреватель", DeviceKind.HEATER, 5, SWITCHING, True),
    StarterDevice("Кондиционер", DeviceKind.AIR_CONDITIONER, 6, CLIMATE, True),
)


class HomeProvisioning:
    """Creates the devices, the dashboard and the preferences of a new account."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory) -> None:
        """Initialize the reaction.

        Args:
            home_uow: Factory producing transactions over the configuration.

        Returns:
            None.
        """
        self._home_uow = home_uow

    async def __call__(self, events: tuple[object, ...]) -> None:
        """Give a home to every account that was just created.

        Args:
            events: Facts recorded by an aggregate.

        Returns:
            None.
        """
        registered = [event for event in events if isinstance(event, UserRegistered)]
        for event in registered:
            await self._provision(event.user_id)

    async def _provision(self, user_id: UserId) -> None:
        async with self._home_uow() as uow:
            devices = [template.build(user_id) for template in STARTER_DEVICES]
            for device in devices:
                await uow.devices.add(device)
            await uow.automation.save(AutomationSettings.create(user_id))
            await uow.preferences.save(UserPreferences.create(user_id))
            await uow.dashboard.save(
                DashboardState.starter(user_id, tuple(device.id for device in devices))
            )
