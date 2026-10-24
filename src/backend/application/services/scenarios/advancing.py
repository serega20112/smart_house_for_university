"""Фоновый шаг сценариев одного дома.

Сценарий — отложенное обещание, и этот шаг — единственный, кто его помнит: он
закрывает те, чей момент настал, следит, достигнута ли цель, и сворачивает их так,
как выбрал человек.

Транзакция никогда не держится во время разговора с платой: сетевой поход не
должен занимать соединение с базой, иначе медленная плата сделала бы это для
каждого сценария каждого аккаунта.

Отказ остаётся тем сценарием, который его вызвал: ожидаемый отказ приложения —
способность, которой нет ни у одного устройства, переставшая отвечать плата, —
переводит сценарий в FAILED, а шаг продолжается, поэтому одно сломанное обещание
не останавливает остальные. То, что не случилось, не записывается как сделанное:
сначала выполняются команды, а агрегат перезаписывается после успеха, и
неполный старт возвращает уже переключённые устройства.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from backend.application.errors import ConcurrentModificationError
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.notification_factory import (
    NotificationFactory,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.messaging.user_notifier import UserNotifier
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.application.services.scenarios.details import (
    EXPECTED_REFUSALS,
    reason_of,
    restorable_states,
    scenario_payload,
)
from backend.application.services.scenarios.settling import ScenarioSettler
from backend.domain.aggregates.device.device import Device
from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.events import EventName
from backend.domain.exceptions import ScenarioAlreadyFinishedError
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.finish_reason import FinishReason


class ScenarioAdvancer:
    """Двигает вперёд все сценарии дома, держащие приоритет."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        notifier: UserNotifier,
        notifications: NotificationFactory,
        clock: Clock,
        settler: ScenarioSettler,
        summary_window_sec: int,
    ) -> None:
        """Собирает фоновый шаг сценариев.

        Args:
            home_uow: Граница транзакции над конфигурацией дома.
            control: Сервис, доводящий способность до железа.
            state_store: Хранилище изменчивого состояния дома.
            realtime: Отправитель событий открытым клиентам.
            dispatcher: Раздатчик записанных фактов подписчикам.
            notifier: Канал доставки уведомлений.
            notifications: Строит текст каждого сообщения.
            clock: Источник текущего момента.
            settler: Сворачивание сценария после финальной стадии.
            summary_window_sec: Кратчайший промежуток между двумя сводками одного
                сценария.
        """
        self._home_uow = home_uow
        self._control = control
        self._state_store = state_store
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._notifier = notifier
        self._notifications = notifications
        self._clock = clock
        self._settler = settler
        self._summary_window_sec = summary_window_sec

    async def advance(self, user_id: UserId) -> None:
        """Двигает каждый сценарий, держащий приоритет, на один шаг вперёд.

        Сценарий, который не может двинуться, помечается сорванным, и шаг идёт
        дальше. Сценарий, проигравший гонку вызову интерфейса в том же такте,
        пропускается: следующий такт прочитает свежий снимок и увидит правду строки.

        Args:
            user_id: Владелец сценариев.
        """
        async with self._home_uow() as uow:
            scenarios = list(await uow.scenarios.list_holding_priority(user_id))
            devices = list(await uow.devices.list_all(user_id))
        state = await self._state_store.read(user_id)
        now = self._clock.now()
        for scenario in scenarios:
            try:
                await self._advance_one(scenario, devices, state, now)
            except ScenarioAlreadyFinishedError:
                continue
            except ConcurrentModificationError:
                continue
            except EXPECTED_REFUSALS as refusal:
                await self._fail(scenario, devices, reason_of(refusal))

    async def _advance_one(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        state: HomeState,
        now: datetime,
    ) -> None:
        """Двигает один сценарий на один шаг вперёд.

        Args:
            scenario: Сценарий на текущей стадии.
            devices: Устройства, которым адресованы его команды.
            state: Как дом выглядел непосредственно перед командами.
            now: Момент такта.
        """
        if scenario.is_due(now):
            await self._start(scenario, devices, state)
            return
        if scenario.is_goal_reached(state.reading):
            await self._finish(scenario, devices, FinishReason.GOAL_REACHED)
            return
        if scenario.has_timed_out(now):
            await self._finish(scenario, devices, FinishReason.DURATION_EXPIRED)
            return
        await self._report_progress(scenario, state.reading.temperature)

    async def _start(self, scenario: Scenario, devices: Sequence[Device], state: HomeState) -> None:
        """Начинает действие, записывая старт только если он удался.

        Состояния устройств снимаются до любого переключения, чтобы поведение
        «вернуть как было» знало, куда именно оно возвращает.

        Args:
            scenario: Сценарий, чей час настал.
            devices: Устройства, которым адресованы команды.
            state: Дом до начала команд.
        """
        captured = {device.id: state.status_of(device) for device in devices}
        try:
            await self._perform_actions(scenario, devices)
        except EXPECTED_REFUSALS as refusal:
            await self._undo_started_devices(scenario, devices, captured)
            raise refusal
        async with self._home_uow() as uow:
            scenario.start(captured)
            await uow.scenarios.update(scenario)
        await self._realtime.publish(
            scenario.user_id, EventName.SCENARIO_STARTED, scenario_payload(scenario)
        )
        await self._dispatcher.dispatch(scenario.pull_events())
        await self._notifier.notify(
            scenario.user_id,
            self._notifications.scenario_started(str(scenario.id), scenario.target),
        )

    async def _perform_actions(self, scenario: Scenario, devices: Sequence[Device]) -> None:
        """Доводит команды сценария до железа.

        Args:
            scenario: Сценарий, чьи команды выполняются.
            devices: Устройства, которым они адресованы.
        """
        for action in scenario.actions:
            await self._control.apply_to_first_matching(
                scenario.user_id, devices, action.capability, manual=False
            )

    async def _undo_started_devices(
        self,
        scenario: Scenario,
        devices: Sequence[Device],
        captured: dict[DeviceId, DeviceStatus],
    ) -> None:
        """Возвращает устройства, которые неполный старт уже переключил.

        Плата отказывает сейчас — именно это и сорвало сценарий, — поэтому откат
        делается по возможности: что плата примет, то вернётся, а что нет —
        доживёт до следующего прохода рабочего.

        Args:
            scenario: Владелец возвращаемых состояний.
            devices: Устройства, которым адресовались команды.
            captured: Состояния устройств до действия сценария.
        """
        wanted = restorable_states(captured)
        if not wanted:
            return
        try:
            await self._control.restore_statuses(scenario.user_id, devices, wanted)
        except EXPECTED_REFUSALS:
            return

    async def _finish(
        self, scenario: Scenario, devices: Sequence[Device], reason: FinishReason
    ) -> None:
        """Останавливает сценарий по намерению и возвращает устройства.

        Args:
            scenario: Сценарий, переходящий в финальную стадию.
            devices: Устройства, которым адресовались команды.
            reason: Почему сценарий перестал действовать.
        """
        async with self._home_uow() as uow:
            scenario.complete(reason.value)
            await uow.scenarios.update(scenario)
        await self._settler.settle(scenario, devices, reason)

    async def _fail(
        self, scenario: Scenario, devices: Sequence[Device], reason: FinishReason
    ) -> None:
        """Записывает, что сценарий не удалось выполнить.

        Устройства, которые сценарий успел переключить, возвращаются в прежнее
        состояние, поэтому сорванный сценарий ничего после себя не оставляет,
        кроме записи о причине.

        Args:
            scenario: Сценарий, выполнение которого не вышло.
            devices: Устройства, которым адресовались команды.
            reason: Почему сценарий перестал действовать.
        """
        try:
            scenario.fail(reason.value)
        except ScenarioAlreadyFinishedError:
            return
        async with self._home_uow() as uow:
            await uow.scenarios.update(scenario)
        await self._settler.settle(scenario, devices, reason, failed=True)

    async def _report_progress(self, scenario: Scenario, temperature: Temperature | None) -> None:
        """Отправляет одно редкое сообщение о ходе идущего сценария.

        Args:
            scenario: Сценарий, проходящий стадии.
            temperature: Что измерили датчики, если измерили.
        """
        allowed = await self._state_store.claim_summary_slot(
            scenario.user_id, f"scenario:{scenario.id}", self._summary_window_sec
        )
        if not allowed:
            return
        await self._notifier.notify(
            scenario.user_id,
            self._notifications.scenario_progress(
                str(scenario.id), None if temperature is None else temperature.celsius
            ),
        )
