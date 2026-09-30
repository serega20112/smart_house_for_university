"""State synchronizer fed by the board connection.

Implements the inbound handler port: updates the runtime, publishes realtime
events and notifies about significant moments. Device names are resolved through
its own unit of work factory because the board pushes data outside of any HTTP
request.
"""

from __future__ import annotations

from typing import Any

from smart_home_backend.application.interface.services import (
    EspGateway,
    EspStateHandler,
    EventBus,
    Notifier,
)
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import notifications
from smart_home_backend.application.services.home_runtime import HomeRuntime
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import DeviceStatus


class HomeStateSynchronizer(EspStateHandler):
    """Keeps the runtime state in sync with what the board reports."""

    def __init__(
        self,
        runtime: HomeRuntime,
        events: EventBus,
        notifier: Notifier,
        uow_factory: UnitOfWorkFactory,
        esp: EspGateway,
    ) -> None:
        """Initialize the synchronizer.

        Args:
            runtime: Runtime state to update.
            events: Publisher of realtime events.
            notifier: Delivery channel for significant events.
            uow_factory: Factory producing units of work for device lookups.
            esp: Gateway used to resynchronize after a reconnect.

        Returns:
            None.
        """
        self._runtime = runtime
        self._events = events
        self._notifier = notifier
        self._uow_factory = uow_factory
        self._esp = esp

    async def on_connected(self) -> None:
        """Handle a new board connection and resynchronize its state.

        Returns:
            None.
        """
        was_offline = not self._runtime.esp_online
        self._runtime.set_esp_online(True)
        await self._events.publish("esp.connected", {"online": True})
        if was_offline:
            await self._notifier.notify(notifications.esp_connected())
        await self._esp.request_state()

    async def on_disconnected(self) -> None:
        """Handle a lost board connection.

        Returns:
            None.
        """
        self._runtime.set_esp_online(False)
        await self._events.publish("esp.disconnected", {"online": False})
        await self._notifier.notify(notifications.esp_disconnected())

    async def on_relay_states(self, states: list[bool]) -> None:
        """Apply reported relay states and publish the affected devices.

        Args:
            states: Relay states ordered by channel.

        Returns:
            None.
        """
        changed = self._runtime.apply_relay_states(states)
        if not changed:
            return
        async with self._uow_factory() as uow:
            devices = list(await uow.devices.list_all())
        by_channel: dict[int, Device] = {
            device.physical_channel: device for device in devices
        }
        for channel in changed:
            device = by_channel.get(channel)
            if device is None:
                continue
            await self._events.publish(
                "device.state_changed",
                {
                    "device_id": device.id,
                    "name": device.name,
                    "channel": channel,
                    "status": self._runtime.device_status(device).value,
                },
            )

    async def on_reading(self, temperature: float | None, humidity: float | None) -> None:
        """Apply reported sensor values and publish what changed.

        Args:
            temperature: Measured temperature or None.
            humidity: Measured relative humidity or None.

        Returns:
            None.
        """
        temperature_changed, humidity_changed = self._runtime.apply_reading(temperature, humidity)
        if temperature_changed:
            await self._events.publish(
                "sensor.temperature_changed",
                {"temperature": self._runtime.state.temperature},
            )
        if humidity_changed:
            await self._events.publish(
                "sensor.humidity_changed", {"humidity": self._runtime.state.humidity}
            )

    async def on_error(self, code: str, message: str) -> None:
        """Publish an error reported by the board.

        Args:
            code: Machine readable error code.
            message: Human readable error description.

        Returns:
            None.
        """
        payload: dict[str, Any] = {
            "code": code,
            "message": message,
            "device_status": DeviceStatus.UNAVAILABLE.value,
        }
        await self._events.publish("esp.error", payload)
