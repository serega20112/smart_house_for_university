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

from backend.application.interface.services.board_report import BoardReport
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.home_device_directory import HomeDeviceDirectory
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.notification_factory import NotificationFactory
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.services.user_notifier import UserNotifier
from backend.domain.events import EventName
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading


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
        was_online = await self._state_store.record_board_online(user_id, True, self._clock.now())
        await self._realtime.publish(user_id, EventName.BOARD_ONLINE, {"board_id": str(board_id)})
        if not was_online:
            await self._notifier.notify(user_id, self._notifications.board_online())

    async def on_disconnected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Handle a lost board connection.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            None.
        """
        await self._state_store.record_board_online(user_id, False, self._clock.now())
        await self._realtime.publish(user_id, EventName.BOARD_OFFLINE, {"board_id": str(board_id)})
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
        changed_channels = await self._state_store.record_relay_report(
            user_id, states, self._clock.now()
        )
        if not changed_channels:
            return
        state = await self._state_store.read(user_id)
        by_channel = await self._devices.by_channel(user_id)
        for channel in changed_channels:
            device = by_channel.get(channel)
            if device is None:
                continue
            await self._realtime.publish(
                user_id,
                EventName.BOARD_RELAY_CHANGED,
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
        changed = await self._state_store.record_background_reading(
            user_id, reading, self._clock.now()
        )
        if changed.temperature is not None:
            await self._realtime.publish(
                user_id,
                EventName.SENSOR_TEMPERATURE_CHANGED,
                {"temperature": changed.temperature.celsius},
            )
        if changed.humidity is not None:
            await self._realtime.publish(
                user_id, EventName.SENSOR_HUMIDITY_CHANGED, {"humidity": changed.humidity.percent}
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
            EventName.BOARD_ERROR,
            {"board_id": str(board_id), "code": code, "message": message},
        )
