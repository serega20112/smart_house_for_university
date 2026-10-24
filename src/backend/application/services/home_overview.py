"""Единый сборщик читающей проекции дома.

И главный экран, и текстовая команда «что делает дом» хотят одно и то же: показания,
устройства с их живым состоянием, настройку автоматизации и идущие сценарии. Раньше каждый
сценарий делал эти четыре чтения сам и сам склеивал ответ — два места, обязанность
держать которые совпадает, а расходятся они незаметно. Здесь сбор один, и оба потребителя
берут готовую проекцию.
"""

from __future__ import annotations

from backend.application.dto.views.device_view import DeviceView
from backend.application.dto.views.home_snapshot_view import HomeSnapshotView
from backend.application.dto.views.reading_view import ReadingView
from backend.application.interfaces.queries.automation_queries import AutomationQueries
from backend.application.interfaces.queries.device_queries import DeviceQueries
from backend.application.interfaces.queries.scenario_queries import ScenarioQueries
from backend.application.interfaces.services.boards.board_availability import BoardAvailability
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.services.system.clock import Clock
from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import UserId


class HomeOverviewQuery:
    """Собирает весь дом одного аккаунта в одну проекцию для показа."""

    def __init__(
        self,
        state_store: HomeStateStore,
        device_queries: DeviceQueries,
        scenario_queries: ScenarioQueries,
        automation_queries: AutomationQueries,
        clock: Clock,
        board_availability: BoardAvailability,
    ) -> None:
        """Инициализирует сборщик.

        Args:
            state_store: Надёжный дом изменчивого состояния.
            device_queries: Чтения конфигурации устройств.
            scenario_queries: Чтения сценариев.
            automation_queries: Чтения настройки автоматизации.
            clock: Источник текущего времени.
            board_availability: Спрос, в сети ли сейчас хоть одна плата дома.
        """
        self._state_store = state_store
        self._devices = device_queries
        self._scenarios = scenario_queries
        self._automation = automation_queries
        self._clock = clock
        self._availability = board_availability

    async def load(self, user_id: UserId) -> HomeSnapshotView:
        """Возвращает снимок дома одного аккаунта.

        Четыре источника читаются раздельно и общей транзакции между Redis и
        PostgreSQL не бывает, поэтому числа могут разойтись на величину одного
        обращения — это осознанное ограничение дешёвого снимка.

        Args:
            user_id: Владелец дома.

        Returns:
            HomeSnapshotView: Всё, что надо показать о доме.
        """
        state = await self._state_store.read(user_id)
        devices = await self._devices.list_all(user_id)
        scenarios = await self._scenarios.list_holding_priority(user_id)
        automation = await self._automation.get(user_id)
        board_online = await self._availability.is_any_online(user_id)
        return HomeSnapshotView(
            reading=_reading_of(state),
            board_online=board_online,
            automation_suspended=state.is_automation_suspended(self._clock.now()),
            devices=tuple(_with_live_status(device, state) for device in devices),
            automation=automation,
            active_scenarios=tuple(scenarios),
        )


def _reading_of(state: HomeState) -> ReadingView:
    """Возвращает значения климата из состояния.

    Args:
        state: Живое состояние дома.

    Returns:
        ReadingView: Значения климата в том виде, в каком они нужны экрану.
    """
    temperature = state.reading.temperature
    humidity = state.reading.humidity
    return ReadingView(
        temperature=None if temperature is None else temperature.celsius,
        humidity=None if humidity is None else humidity.percent,
    )


def _with_live_status(device: DeviceView, state: HomeState) -> DeviceView:
    """Возвращает устройство с состоянием, которое знает живое состояние дома.

    Args:
        device: Устройство таким, каким оно сохранено.
        state: Живое состояние дома.

    Returns:
        DeviceView: Устройство с состоянием, в котором оно находится сейчас.
    """
    return device.with_status(state.status_for(device.id, device.channel, device.board_id))
