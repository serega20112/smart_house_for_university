"""Handlers of the intents that talk about the climate of the home."""

from __future__ import annotations

from smart_home.application.dto.home import CommandReply
from smart_home.application.errors import CommandNotUnderstoodError
from smart_home.application.ports.language import ClarificationReason, CommandUnderstanding, Intent
from smart_home.application.ports.services import HomeStateStore
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from smart_home.application.services.device_control import DeviceControlService
from smart_home.domain.climate.automation_settings import AutomationSettings
from smart_home.domain.climate.climate_demand import DemandCalculator
from smart_home.domain.climate.humidity import Humidity
from smart_home.domain.devices.capability import Capability
from smart_home.domain.identifiers import UserId


class SetClimateTargetHandler:
    """Answers "make it twenty degrees" and "sixty percent humidity".

    One class serves both dimensions and tells them apart by a flag, which is why
    there is no family of near identical handlers differing by one number.
    """

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        demands: DemandCalculator,
        measures_temperature: bool,
    ) -> None:
        """Initialize the handler.

        Args:
            home_uow: Factory producing transactions over the configuration.
            demands: Model component deciding what a target implies.
            measures_temperature: Whether this handler deals with the temperature
                rather than with the humidity.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._demands = demands
        self._is_temperature = measures_temperature

    @property
    def intent(self) -> Intent:
        """Return the intent this handler serves.

        Returns:
            Intent: Intent of the handler.
        """
        return Intent.SET_TEMPERATURE if self._is_temperature else Intent.SET_HUMIDITY

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Store the target the sentence asked for.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: The target that was stored.

        Raises:
            CommandNotUnderstoodError: When the sentence carries no value.
        """
        async with self._home_uow() as uow:
            settings = await uow.automation.get(user_id)
            current = settings if settings is not None else AutomationSettings.create(user_id)
            if self._is_temperature:
                if parsed.temperature is None:
                    raise CommandNotUnderstoodError(ClarificationReason.MISSING_TEMPERATURE)
                current.aim_at_temperature(parsed.temperature)
                stored: float = parsed.temperature.celsius
            else:
                if parsed.humidity is None:
                    raise CommandNotUnderstoodError(ClarificationReason.MISSING_HUMIDITY)
                current.aim_at_humidity(Humidity(parsed.humidity))
                stored = parsed.humidity
            await uow.automation.save(current)
        field = "temperature" if self._is_temperature else "humidity"
        return CommandReply(intent=self.intent, answer="", details={field: stored})


class RunCapabilityHandler:
    """Answers "make it colder" and "switch the air conditioner on"."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
        demands: DemandCalculator,
    ) -> None:
        """Initialize the handler.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.
            state_store: Durable home of the volatile state.
            demands: Model component deciding which capability a target implies.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control
        self._state_store = state_store
        self._demands = demands

    async def __call__(self, user_id: UserId, parsed: CommandUnderstanding) -> CommandReply:
        """Perform the capability the sentence asks for.

        A sentence naming a target without naming a direction is resolved against
        the measured temperature, which is a decision of the model rather than a
        guess made by the router.

        Args:
            user_id: Owner the command is executed for.
            parsed: What the pipeline made of the sentence.

        Returns:
            CommandReply: The device that was driven.

        Raises:
            CommandNotUnderstoodError: When no capability can be worked out.
        """
        capability = parsed.capability or await self._from_target(user_id, parsed)
        if capability is None:
            raise CommandNotUnderstoodError(ClarificationReason.MISSING_CAPABILITY)
        async with self._home_uow() as uow:
            devices = list(await uow.devices.list_all(user_id))
        view = await self._control.apply_to_first_matching(user_id, devices, capability)
        return CommandReply(
            intent=Intent.RUN_CAPABILITY,
            answer="",
            details={"device": view.name, "capability": capability.value},
        )

    async def _from_target(
        self, user_id: UserId, parsed: CommandUnderstanding
    ) -> Capability | None:
        if parsed.temperature is None:
            return None
        state = await self._state_store.read(user_id)
        measured = state.reading.temperature
        return self._demands.capability_towards(
            parsed.temperature.celsius, None if measured is None else measured.celsius
        )
