"""Сворачивание сценария: возврат устройств и сообщение человеку.

Один путь для «дошло до цели», «истекло по времени», «сломалось» и «отменили»,
потому что после того как агрегат записан, различий не остаётся: железо надо
вернуть, интерфейс — известить, подписчиков — раздать.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.notification_factory import (
    NotificationFactory,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.messaging.user_notifier import UserNotifier
from backend.application.services.device_control import DeviceControlService
from backend.application.services.scenarios.details import scenario_payload
from backend.domain.aggregates.device.device import Device
from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.events import EventName
from backend.domain.value_objects.scenario.finish_reason import FinishReason


class ScenarioSettler:
    """Доводит до конца сценарий, который больше не действует."""

    def __init__(
        self,
        control: DeviceControlService,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
    ) -> None:
        """Собирает сворачивание сценария.

        Args:
            control: Сервис, доводящий способность до железа.
            realtime: Отправитель событий открытым клиентам.
            dispatcher: Раздатчик записанных фактов подписчикам.
            notifier: Канал доставки уведомлений.
            notifications: Строит текст каждого сообщения.
        """
        self._control = control
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._notifier = notifier
        self._notifications = notifications

    async def settle(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        reason: FinishReason,
        *,
        failed: bool = False,
    ) -> None:
        """Возвращает устройства, отправляет событие и относит сообщение.

        Args:
            scenario: Сценарий, перешедший в финальную стадию.
            devices: Устройства, которых касались его команды.
            reason: Почему сценарий перестал действовать.
            failed: True для провала — текст берётся из ветки неудачи.
        """
        await self._control.restore_statuses(
            scenario.user_id, devices, scenario.statuses_to_restore()
        )
        await self._realtime.publish(
            scenario.user_id, EventName.SCENARIO_FINISHED, scenario_payload(scenario)
        )
        await self._dispatcher.dispatch(scenario.pull_events())
        message = (
            self._notifications.scenario_failed(str(scenario.id), reason.value)
            if failed
            else self._notifications.scenario_finished(str(scenario.id), reason.value)
        )
        await self._notifier.notify(scenario.user_id, message)
