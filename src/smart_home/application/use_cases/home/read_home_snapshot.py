"""Read the whole home of one account in a single snapshot.

The main screen of the interface shows the climate, the devices, the automation
and the running scenarios at once. Assembling that from four different readers
would let the numbers on the screen come from moments that do not belong
together, so one use case reads them and hands over a single value.
"""

from __future__ import annotations

from smart_home.application.dto.device import DeviceView
from smart_home.application.dto.home import HomeSnapshotView, ReadingView
from smart_home.application.ports.queries.automation import AutomationQueries
from smart_home.application.ports.queries.devices import DeviceQueries
from smart_home.application.ports.queries.scenarios import ScenarioQueries
from smart_home.application.ports.services import Clock, HomeStateStore
from smart_home.domain.climate.home_state import HomeState
from smart_home.domain.identifiers import UserId


class ReadHomeSnapshotUseCase:
    """Assembles everything the main screen of the interface shows."""

    def __init__(
        self,
        state_store: HomeStateStore,
        device_queries: DeviceQueries,
        scenario_queries: ScenarioQueries,
        automation_queries: AutomationQueries,
        clock: Clock,
    ) -> None:
        """Initialize the use case.

        Args:
            state_store: Durable home of the volatile state.
            device_queries: Reads of the device configuration.
            scenario_queries: Reads of the scenarios.
            automation_queries: Reads of the automation configuration.
            clock: Source of the current time.

        Returns:
            None.
        """
        self._state_store = state_store
        self._devices = device_queries
        self._scenarios = scenario_queries
        self._automation = automation_queries
        self._clock = clock

    async def execute(self, user_id: UserId) -> HomeSnapshotView:
        """Return the snapshot of the home of one account.

        Args:
            user_id: Owner of the home.

        Returns:
            HomeSnapshotView: Everything the interface has to render.
        """
        state = await self._state_store.read(user_id)
        devices = await self._devices.list_all(user_id)
        scenarios = await self._scenarios.list_holding_priority(user_id)
        automation = await self._automation.get(user_id)
        return HomeSnapshotView(
            reading=_reading_of(state),
            board_online=state.board_online,
            automation_suspended=state.is_automation_suspended(self._clock.now()),
            devices=tuple(_with_live_status(device, state) for device in devices),
            automation=automation,
            active_scenarios=tuple(scenarios),
        )


def _reading_of(state: HomeState) -> ReadingView:
    """Return the climate values of a state.

    Args:
        state: Live state of the home.

    Returns:
        ReadingView: Climate values as the interface needs them.
    """
    temperature = state.reading.temperature
    humidity = state.reading.humidity
    return ReadingView(
        temperature=None if temperature is None else temperature.celsius,
        humidity=None if humidity is None else humidity.percent,
    )


def _with_live_status(device: DeviceView, state: HomeState) -> DeviceView:
    """Return a device carrying the status the live state knows about.

    Args:
        device: Device as it was stored.
        state: Live state of the home.

    Returns:
        DeviceView: Device with the status it is in right now.
    """
    return device.with_status(state.status_for(device.id, device.channel))
