"""Handlers of the intents that ask what the home is doing."""

from __future__ import annotations

from smart_home.application.dto.home import CommandReply
from smart_home.application.ports.language import CommandUnderstanding, Intent
from smart_home.application.ports.queries.automation import AutomationQueries
from smart_home.application.ports.queries.devices import DeviceQueries
from smart_home.application.ports.queries.scenarios import ScenarioQueries
from smart_home.application.ports.services import Clock, HomeStateStore
from smart_home.domain.identifiers import UserId


class DescribeHomeHandler:
    """Answers "what is the state of the house"."""

    def __init__(
        self,
        state_store: HomeStateStore,
        device_queries: DeviceQueries,
        scenario_queries: ScenarioQueries,
        automation_queries: AutomationQueries,
        clock: Clock,
    ) -> None:
        """Initialize the handler.

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

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Describe the live state of the home.

        The reading comes from the state store and never from a full home
        snapshot, so asking one number does not drag the whole house along.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: What the home is doing right now.
        """
        del parsed
        state = await self._state_store.read(user_id)
        devices = await self._devices.list_all(user_id)
        scenarios = await self._scenarios.list_holding_priority(user_id)
        automation = await self._automation.get(user_id)
        measured = state.reading.temperature
        return CommandReply(
            intent=Intent.DESCRIBE_HOME,
            answer="",
            details={
                "board_online": state.board_online,
                "automation_suspended": state.is_automation_suspended(self._clock.now()),
                "temperature": None if measured is None else measured.celsius,
                "humidity": (
                    None if state.reading.humidity is None else state.reading.humidity.percent
                ),
                "devices_on": [device.name for device in devices if device.status.is_active],
                "automation_enabled": automation.enabled,
                "active_scenarios": [str(scenario.id) for scenario in scenarios],
            },
        )


class ReadTemperatureHandler:
    """Answers "how warm is it"."""

    def __init__(self, state_store: HomeStateStore) -> None:
        """Initialize the handler.

        Args:
            state_store: Durable home of the volatile state.

        Returns:
            None.
        """
        self._state_store = state_store

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Return the measured temperature.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: The measured temperature.
        """
        del parsed
        state = await self._state_store.read(user_id)
        measured = state.reading.temperature
        return CommandReply(
            intent=Intent.READ_TEMPERATURE,
            answer="",
            details={"temperature": None if measured is None else measured.celsius},
        )


class ReadHumidityHandler:
    """Answers "how wet is it"."""

    def __init__(self, state_store: HomeStateStore) -> None:
        """Initialize the handler.

        Args:
            state_store: Durable home of the volatile state.

        Returns:
            None.
        """
        self._state_store = state_store

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Return the measured humidity.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: The measured humidity.
        """
        del parsed
        state = await self._state_store.read(user_id)
        measured = state.reading.humidity
        return CommandReply(
            intent=Intent.READ_HUMIDITY,
            answer="",
            details={"humidity": None if measured is None else measured.percent},
        )
