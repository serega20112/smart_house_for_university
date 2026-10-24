"""Держит живое состояние дома в ладу с его платами.

Это один сервис, который потребляёт всё, что сообщают платы. Он заменил пару классов,
чья работа была лишь передавать зависимости друг другу: объект один, живёт он столько же,
сколько приложение, и служит каждой плате каждого аккаунта.

Своего состояния сервис не ведёт. Всё, что он узнаёт, пишется прямо в хранилище
состояния — поэтому перезапуск незаметен человеку и несколько процессов могут договориться
о том, что делают реле.
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
    """Применяет всё, о чём сообщают платы, и объявляет изменившееся."""

    def __init__(
        self,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        devices_of_home: HomeDeviceDirectory,
    ) -> None:
        """Инициализирует сервис.

        Args:
            state_store: Надёжный дом изменчивого состояния.
            realtime: Издатель событий в открытые соединения.
            notifier: Канал доставки уведомлений.
            notifications: Строит формулировки каждого сообщения.
            clock: Источник текущего времени.
            devices_of_home: Дешёвые чтения конфигурации, чтобы сообщение о реле
                переводилось в имя устройства.
        """
        self._state_store = state_store
        self._realtime = realtime
        self._notifier = notifier
        self._notifications = notifications
        self._clock = clock
        self._devices = devices_of_home

    async def on_connected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Реагирует на новое соединение платы.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
        """
        was_online = await self._state_store.record_board_online(user_id, True, self._clock.now())
        await self._realtime.publish(user_id, EventName.BOARD_ONLINE, {"board_id": str(board_id)})
        if not was_online:
            await self._notifier.notify(user_id, self._notifications.board_online())

    async def on_disconnected(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Реагирует на потерю соединения платы.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
        """
        await self._state_store.record_board_online(user_id, False, self._clock.now())
        await self._realtime.publish(user_id, EventName.BOARD_OFFLINE, {"board_id": str(board_id)})
        await self._notifier.notify(user_id, self._notifications.board_offline())

    async def on_relay_states(
        self, user_id: UserId, board_id: EspDeviceId, states: list[bool]
    ) -> None:
        """Принимает сообщённые положения реле и объявляет изменившиеся устройства.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            states: Положения контактов по порядку каналов.
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
        """Принимает сообщение датчиков и объявляет изменившееся.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            reading: Измеренные значения.
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
        """Публикует отказ, о котором сообщила плата.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            code: Машинночитаемый код отказа.
            message: Описание отказа человеческими словами.
        """
        await self._realtime.publish(
            user_id,
            EventName.BOARD_ERROR,
            {"board_id": str(board_id), "code": code, "message": message},
        )
