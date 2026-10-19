"""Keeping the live state of a home in step with its boards.

This is a single service that consumes everything the boards report. It replaced a
pair of classes whose only job was to hand dependencies to each other: there is one
object, it lives as long as the application, and it serves every board of every
account.

The service owns no state of its own. Everything it learns is written straight to
the state store, which is what makes a restart invisible to the user and lets
several workers agree on what the relays are doing.
"""

from __future__ import annotations

from backend.application.ports.boards import BoardReport
from backend.application.ports.events import NotificationFactory, RealtimePublisher, UserNotifier
from backend.application.ports.home import HomeDeviceDirectory
from backend.application.ports.services import Clock, HomeStateStore
from backend.domain.climate.climate_reading import ClimateReading
from backend.domain.identifiers import EspDeviceId, UserId

BOARD_ONLINE_EVENT = "board.online"
BOARD_OFFLINE_EVENT = "board.offline"
RELAY_CHANGED_EVENT = "board.relay_changed"
TEMPERATURE_EVENT = "sensor.temperature_changed"
HUMIDITY_EVENT = "sensor.humidity_changed"
BOARD_ERROR_EVENT = "board.error"


class HomeStateService(BoardReport):
    """Applies everything the boards report and announces what changed."""

    def __init__(
        self,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        devices_of_home: HomeDeviceDirectory,
    ) -> None:
        """Initialize the service.

        Args:
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.
            notifier: Delivery channel for notifications.
            notifications: Builds the wording of every message.
            clock: Source of the current time.
            devices_of_home: Cheap reads of the configuration, so a relay report can
                be translated into a device name.

        Returns:
            None.
        """
        self._state_store = state_store
        self._realtime = realtime
        self._notifier = notifier
        self._notifications = notifications
        self._clock = clock
        self._devices = devices_of_home

    async def on_connected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Handle a new board connection.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """
        state = await self._state_store.load(user_id)
        was_offline = not state.board_online
        state.set_board_available(True, self._clock.now())
        await self._state_store.save(state)
        await self._realtime.publish(user_id, BOARD_ONLINE_EVENT, {"board_id": str(board_id)})
        if was_offline:
            await self._notifier.notify(user_id, self._notifications.board_online())

    async def on_disconnected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Handle a lost board connection.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """
        state = await self._state_store.load(user_id)
        state.set_board_available(False, self._clock.now())
        await self._state_store.save(state)
        await self._realtime.publish(user_id, BOARD_OFFLINE_EVENT, {"board_id": str(board_id)})
        await self._notifier.notify(user_id, self._notifications.board_offline())

    async def on_relay_states(
        self, user_id: UserId, board_id: EspDeviceId, states: list[bool]
    ) -> None:
        """Apply reported relay positions and announce the devices that changed.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            states: Contact positions ordered by channel.

        Returns:
            None.
        """
        state = await self._state_store.load(user_id)
        changed = state.apply_relay_report(states, self._clock.now())
        if not changed:
            return
        await self._state_store.save(state)
        by_channel = await self._devices.by_channel(user_id)
        for channel in changed:
            device = by_channel.get(channel)
            if device is None:
                continue
            await self._realtime.publish(
                user_id,
                RELAY_CHANGED_EVENT,
                {
                    "board_id": str(board_id),
                    "device_id": str(device.id),
                    "name": device.name,
                    "channel": channel,
                    "status": state.status_of(device).value,
                },
            )

    async def on_reading(
        self, user_id: UserId, board_id: EspDeviceId, reading: ClimateReading
    ) -> None:
        """Apply a sensor report and announce what changed.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            reading: Measured values.

        Returns:
            None.
        """
        del board_id
        state = await self._state_store.load(user_id)
        changed = state.apply_reading(reading, self._clock.now())
        await self._state_store.save(state)
        if changed.temperature is not None:
            await self._realtime.publish(
                user_id, TEMPERATURE_EVENT, {"temperature": changed.temperature.celsius}
            )
        if changed.humidity is not None:
            await self._realtime.publish(
                user_id, HUMIDITY_EVENT, {"humidity": changed.humidity.percent}
            )

    async def on_error(
        self, user_id: UserId, board_id: EspDeviceId, code: str, message: str
    ) -> None:
        """Publish an error reported by a board.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.
            code: Machine readable error code.
            message: Human readable error description.

        Returns:
            None.
        """
        await self._realtime.publish(
            user_id,
            BOARD_ERROR_EVENT,
            {"board_id": str(board_id), "code": code, "message": message},
        )
