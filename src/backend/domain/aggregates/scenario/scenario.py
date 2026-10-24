"""Агрегат отложенного сценария.

Сценарий — обещание, данное себе на потом: «через полчаса сделай двадцать
градусов». Агрегат владеет этим обещанием: он знает, когда должен начаться, когда
цель считается достигнутой, когда время вышло и что делать с устройствами после,
и отказывает любому переходу, который смысла не имеет.

Вне агрегата его статус, снимок состояний и действия не меняет никто: правило
нельзя обойти присваиванием поля из вызывающего кода.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Self

from backend.domain.events import ScenarioFinished, ScenarioScheduled, ScenarioStarted
from backend.domain.exceptions import (
    IllegalScenarioTransitionError,
    ScenarioAlreadyFinishedError,
)
from backend.domain.identifiers import DeviceId, ScenarioId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus

GOAL_TOLERANCE_C = 0.5
MAX_TARGET_LENGTH = 120


@dataclass
class Scenario:
    """Обещание изменить климат одного дома в более поздний момент.

    Attributes:
        id: Идентификатор, выданный при создании.
        user_id: Владелец сценария; часть агрегата, чтобы ни один метод не
            спрашивал, чей дом он ведёт.
        status: Этап, на котором сценарий находится.
        created_at: Момент, когда сценарий сохранили.
        start_at: Момент, когда сценарий начинает действовать.
        duration_minutes: Сколько ему разрешено идти, или None без границы.
        target: Место или предмет, который назвал человек, или None.
        completion_behavior: Что будет с устройствами после.
        actions: Действия, которые сценарий выполняет после начала.
        captured_statuses: Состояния устройств, снятые до начала; нужны
            поведению возврата.
        _events: Факты, записанные с момента загрузки сценария.
    """

    id: ScenarioId
    user_id: UserId
    status: ScenarioStatus
    created_at: datetime
    start_at: datetime
    duration_minutes: int | None = None
    target: str | None = None
    completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION
    actions: tuple[ScenarioAction, ...] = ()
    captured_statuses: dict[DeviceId, DeviceStatus] = field(default_factory=dict)
    version: int = 0
    _events: list[ScenarioScheduled | ScenarioStarted | ScenarioFinished] = field(
        default_factory=list, repr=False, compare=False
    )

    @property
    def holds_control_priority(self) -> bool:
        """Сообщает, ставит ли сценарий себя выше автоматики."""
        return self.status.holds_control_priority

    @property
    def ends_at(self) -> datetime | None:
        """Возвращает момент, когда у сценария кончится время."""
        if self.duration_minutes is None:
            return None
        return self.start_at + timedelta(minutes=self.duration_minutes)

    def is_due(self, now: datetime) -> bool:
        """Сообщает, наступило ли время начать.

        Args:
            now: Момент, относительно которого решают.

        Returns:
            bool: True, когда сценарий должен начать действовать.
        """
        return self.status is ScenarioStatus.PENDING and now >= self.start_at

    def has_timed_out(self, now: datetime) -> bool:
        """Сообщает, вышло ли время, отведённое сценарию.

        Args:
            now: Момент, относительно которого решают.

        Returns:
            bool: True, когда длительность истекла.
        """
        end = self.ends_at
        return end is not None and now >= end

    def is_goal_reached(self, reading: ClimateReading) -> bool:
        """Сообщает, достигнута ли каждая запрошенная температура.

        Args:
            reading: Текущие показания датчиков.

        Returns:
            bool: True, когда ждать больше нечего.
        """
        measured = reading.temperature
        if measured is None:
            return False
        return all(
            action.target_temperature is None
            or measured.distance_to(action.target_temperature) <= GOAL_TOLERANCE_C
            for action in self.actions
        )

    def start(self, current_statuses: dict[DeviceId, DeviceStatus]) -> ScenarioStarted:
        """Начинает действовать в доме.

        Состояния, в которых устройства были за мгновение до этого, снимаются
        здесь, а не у вызывающего: поведение возврата опирается на снимок, и только
        агрегат знает, понадобится ли он ему.

        Args:
            current_statuses: Состояние каждого устройства прямо перед стартом.

        Returns:
            ScenarioStarted: Записанный факт.

        Raises:
            IllegalScenarioTransitionError: Когда сценарий не ожидает начала.
        """
        self._require_transition(ScenarioStatus.PENDING, ScenarioStatus.RUNNING)
        self.captured_statuses = dict(current_statuses)
        self.status = ScenarioStatus.RUNNING
        event = ScenarioStarted(user_id=self.user_id, scenario_id=self.id)
        self._events.append(event)
        return event

    def complete(self, reason: str) -> ScenarioFinished:
        """Завершает сценарий успешно.

        Args:
            reason: Почему сценарий завершился.

        Returns:
            ScenarioFinished: Записанный факт.

        Raises:
            IllegalScenarioTransitionError: Когда сценарий так и не начался.
        """
        self._require_transition(ScenarioStatus.RUNNING, ScenarioStatus.COMPLETED)
        return self._finish(ScenarioStatus.COMPLETED, reason)

    def cancel(self) -> ScenarioFinished:
        """Снимает сценарий до того, как он завершился.

        Отменить идущий сценарий можно и это нормально: человек передумал.
        Агрегат отказывает только в повторной отмене.

        Returns:
            ScenarioFinished: Записанный факт.

        Raises:
            ScenarioAlreadyFinishedError: Когда сценарий уже завершился.
        """
        if self.status.is_final:
            raise ScenarioAlreadyFinishedError(str(self.id), self.status.value)
        return self._finish(ScenarioStatus.CANCELLED, "cancelled_by_user")

    def fail(self, reason: str) -> ScenarioFinished:
        """Записывает, что сценарий выполнить не удалось.

        Args:
            reason: Почему не удалось.

        Returns:
            ScenarioFinished: Записанный факт.

        Raises:
            IllegalScenarioTransitionError: Когда сценарий уже завершился.
        """
        if self.status.is_final:
            raise ScenarioAlreadyFinishedError(str(self.id), self.status.value)
        return self._finish(ScenarioStatus.FAILED, reason)

    def statuses_to_restore(self) -> dict[DeviceId, DeviceStatus]:
        """Возвращает состояния, в которые устройства нужно вернуть.

        Returns:
            dict[DeviceId, DeviceStatus]: Состояния возврата; пусто, когда
            устройства оставляют автоматике.
        """
        restored: dict[DeviceId, DeviceStatus] = {}
        for device_id, captured in self.captured_statuses.items():
            target = self.completion_behavior.status_to_apply(captured)
            if target is not None:
                restored[device_id] = target
        if self.completion_behavior is CompletionBehavior.SWITCH_EVERYTHING_OFF:
            return dict.fromkeys(self.captured_statuses, DeviceStatus.OFF)
        return restored

    def pull_events(self) -> tuple[ScenarioScheduled | ScenarioStarted | ScenarioFinished, ...]:
        """Возвращает записанные факты и забывает их.

        Returns:
            tuple[ScenarioScheduled | ScenarioStarted | ScenarioFinished, ...]:
            Факты, записанные с прошлого обращения.
        """
        recorded = tuple(self._events)
        self._events.clear()
        return recorded

    def _finish(self, status: ScenarioStatus, reason: str) -> ScenarioFinished:
        self.status = status
        event = ScenarioFinished(
            user_id=self.user_id,
            scenario_id=self.id,
            status=status.value,
            reason=reason,
        )
        self._events.append(event)
        return event

    def _require_transition(self, current: ScenarioStatus, requested: ScenarioStatus) -> None:
        if self.status is not current:
            raise IllegalScenarioTransitionError(str(self.id), self.status.value, requested.value)

    @classmethod
    def schedule(
        cls,
        user_id: UserId,
        created_at: datetime,
        delay_minutes: int | None = None,
        actions: tuple[ScenarioAction, ...] = (),
        target: str | None = None,
        completion_behavior: CompletionBehavior = CompletionBehavior.LEAVE_TO_AUTOMATION,
        duration_minutes: int | None = None,
    ) -> Self:
        """Строит сценарий, который ждёт своего момента.

        Args:
            user_id: Владелец сценария.
            created_at: Момент, когда сценарий попросили.
            delay_minutes: Сколько ждать до действия.
            actions: Действия, которые нужно выполнить после начала.
            target: Место или предмет, который назвал человек.
            completion_behavior: Что будет с устройствами после.
            duration_minutes: Сколько сценарию разрешено идти.

        Returns:
            Self: Созданный сценарий.

        Raises:
            ValueError: Когда названное место длиннее разрешённого моделью.
        """
        if target is not None and len(target.strip()) > MAX_TARGET_LENGTH:
            raise ValueError(f"scenario target is longer than {MAX_TARGET_LENGTH} characters")
        delay = delay_minutes if delay_minutes and delay_minutes > 0 else 0
        scenario = cls(
            id=ScenarioId.generate(),
            user_id=user_id,
            status=ScenarioStatus.PENDING,
            created_at=created_at,
            start_at=created_at + timedelta(minutes=delay),
            duration_minutes=duration_minutes,
            target=None if target is None else target.strip() or None,
            completion_behavior=completion_behavior,
            actions=actions,
        )
        scenario._events.append(ScenarioScheduled(user_id=user_id, scenario_id=scenario.id))
        return scenario

    @classmethod
    def action_for(
        cls, capability: object, target_temperature: Temperature | None = None
    ) -> ScenarioAction:
        """Строит единственное действие простого сценария.

        Args:
            capability: Способность, о которой просит сценарий.
            target_temperature: Температура, к которой действие идёт.

        Returns:
            ScenarioAction: Действие, которое кладут в сценарий.
        """
        return ScenarioAction(capability=capability, target_temperature=target_temperature)
