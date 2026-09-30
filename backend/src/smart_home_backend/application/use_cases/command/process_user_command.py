"""Process a free-form user command."""

from __future__ import annotations

from smart_home_backend.application.dto.command import CommandResult, ProcessUserCommand
from smart_home_backend.application.dto.scenario import CreateScenarioCommand
from smart_home_backend.application.interface.services import ParsedCommand
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import CommandInterpreter
from smart_home_backend.application.use_cases.climate import (
    RunClimateCapabilityUseCase,
    SetTargetHumidityUseCase,
    SetTargetTemperatureUseCase,
)
from smart_home_backend.application.use_cases.device import (
    SetDeviceModeUseCase,
    TurnAllDevicesUseCase,
    TurnDeviceOffUseCase,
    TurnDeviceOnUseCase,
)
from smart_home_backend.application.use_cases.query import (
    GetActiveScenariosUseCase,
    GetHomeSnapshotUseCase,
)
from smart_home_backend.application.use_cases.scenario import (
    CancelScenarioUseCase,
    CreateScenarioUseCase,
)
from smart_home_backend.domain.enums.device import Capability
from smart_home_backend.domain.enums.intent import Intent
from smart_home_backend.domain.enums.operation import ClarificationReason, OperationStatus
from smart_home_backend.domain.policies import capability_for_target, find_device_by_name


class ProcessUserCommandUseCase:
    """Routes an interpreted command to the matching use case.

    Web, Telegram and a future voice interface all call this use case, so the
    command path stays identical no matter where the request came from.
    """

    def __init__(
        self,
        interpreter: CommandInterpreter,
        uow_factory: UnitOfWorkFactory,
        get_home_snapshot: GetHomeSnapshotUseCase,
        get_active_scenarios: GetActiveScenariosUseCase,
        turn_device_on: TurnDeviceOnUseCase,
        turn_device_off: TurnDeviceOffUseCase,
        set_device_mode: SetDeviceModeUseCase,
        turn_all_devices: TurnAllDevicesUseCase,
        set_target_temperature: SetTargetTemperatureUseCase,
        set_target_humidity: SetTargetHumidityUseCase,
        run_climate_capability: RunClimateCapabilityUseCase,
        create_scenario: CreateScenarioUseCase,
        cancel_scenario: CancelScenarioUseCase,
    ) -> None:
        """Initialize the use case.

        Args:
            interpreter: Natural language pipeline.
            uow_factory: Factory producing units of work.
            get_home_snapshot: Read side returning the live state.
            get_active_scenarios: Read side returning active scenarios.
            turn_device_on: Device command.
            turn_device_off: Device command.
            set_device_mode: Device command.
            turn_all_devices: Device command.
            set_target_temperature: Climate target command.
            set_target_humidity: Climate target command.
            run_climate_capability: Climate capability command.
            create_scenario: Scenario command.
            cancel_scenario: Scenario command.

        Returns:
            None.
        """
        self._interpreter = interpreter
        self._uow_factory = uow_factory
        self._get_home_snapshot = get_home_snapshot
        self._get_active_scenarios = get_active_scenarios
        self._turn_device_on = turn_device_on
        self._turn_device_off = turn_device_off
        self._set_device_mode = set_device_mode
        self._turn_all_devices = turn_all_devices
        self._set_target_temperature = set_target_temperature
        self._set_target_humidity = set_target_humidity
        self._run_climate_capability = run_climate_capability
        self._create_scenario = create_scenario
        self._cancel_scenario = cancel_scenario

    async def execute(self, command: ProcessUserCommand) -> CommandResult:
        """Interpret and execute a free-form command.

        Args:
            command: Raw user request.

        Returns:
            CommandResult: Structured answer for the calling interface.
        """
        interpretation = await self._interpreter.interpret(command.text)
        if not interpretation.is_executable or interpretation.intent is None:
            intent = interpretation.intent
            return CommandResult.needs_clarification(
                interpretation.clarification or ClarificationReason.UNRECOGNIZED_INTENT,
                intent=None if intent is None else intent.value,
                confidence=interpretation.confidence,
                text=command.text,
            )

        return await self._route(interpretation.intent, interpretation.parameters)

    async def _route(self, intent: Intent, parameters: ParsedCommand) -> CommandResult:
        if intent is Intent.TURN_ON or intent is Intent.TURN_OFF:
            return await self._switch_device(intent, parameters.device_ref)
        if intent is Intent.TURN_ON_ALL:
            return await self._switch_all(True)
        if intent is Intent.TURN_OFF_ALL:
            return await self._switch_all(False)
        if intent is Intent.SET_TEMPERATURE:
            return await self._apply_temperature(parameters)
        if intent is Intent.SET_HUMIDITY:
            return await self._apply_humidity(parameters)
        if intent is Intent.COOL or intent is Intent.HEAT:
            return await self._apply_climate_intent(intent, parameters)
        if intent is Intent.GET_STATUS:
            return await self._describe_state()
        if intent is Intent.GET_TEMPERATURE:
            return await self._describe_temperature()
        if intent is Intent.GET_HUMIDITY:
            return await self._describe_humidity()
        if intent is Intent.CREATE_SCENARIO:
            return await self._apply_scenario_intent(parameters)
        return await self._cancel_latest_scenario()

    async def _switch_device(self, intent: Intent, device_ref: str | None) -> CommandResult:
        async with self._uow_factory() as uow:
            devices = list(await uow.devices.list_all())
        device = find_device_by_name(devices, device_ref or "")
        if device is None:
            return CommandResult.needs_clarification(
                ClarificationReason.UNKNOWN_DEVICE, intent=intent.value, device=device_ref
            )
        use_case = self._turn_device_on if intent is Intent.TURN_ON else self._turn_device_off
        result = await use_case.execute(device.id)
        return CommandResult(
            status=result.status, intent=intent.value, details={"device": result.device}
        )

    async def _switch_all(self, on: bool) -> CommandResult:
        turn_all = await self._turn_all_devices.execute(on)
        devices = [result.device for result in turn_all.switched if result.device is not None]
        status = OperationStatus.SUCCESS if devices else OperationStatus.UNSUPPORTED
        intent = Intent.TURN_ON_ALL if on else Intent.TURN_OFF_ALL
        return CommandResult(status=status, intent=intent.value, details={"devices": devices})

    async def _apply_temperature(self, parameters: ParsedCommand) -> CommandResult:
        if parameters.duration_minutes is not None:
            return await self._schedule(parameters, Intent.SET_TEMPERATURE)
        if parameters.temperature is None:
            return CommandResult.needs_clarification(
                ClarificationReason.MISSING_TEMPERATURE, intent=Intent.SET_TEMPERATURE.value
            )
        status, _ = await self._set_target_temperature.execute(parameters.temperature)
        return CommandResult(
            status=status,
            intent=Intent.SET_TEMPERATURE.value,
            details={"temperature": parameters.temperature},
        )

    async def _apply_humidity(self, parameters: ParsedCommand) -> CommandResult:
        if parameters.humidity is None:
            return CommandResult.needs_clarification(
                ClarificationReason.MISSING_HUMIDITY, intent=Intent.SET_HUMIDITY.value
            )
        status, _ = await self._set_target_humidity.execute(parameters.humidity)
        return CommandResult(
            status=status,
            intent=Intent.SET_HUMIDITY.value,
            details={"humidity": parameters.humidity},
        )

    async def _apply_climate_intent(
        self, intent: Intent, parameters: ParsedCommand
    ) -> CommandResult:
        capability = await self._capability_for(intent, parameters.temperature)
        if capability is None:
            return CommandResult.needs_clarification(
                ClarificationReason.MISSING_CAPABILITY, intent=intent.value
            )
        result = await self._run_climate_capability.execute(capability)
        return CommandResult(
            status=result.status, intent=intent.value, details={"device": result.device}
        )

    async def _apply_scenario_intent(self, parameters: ParsedCommand) -> CommandResult:
        return await self._schedule(parameters, Intent.CREATE_SCENARIO)

    async def _schedule(
        self, parameters: ParsedCommand, intent: Intent
    ) -> CommandResult:
        capability = await self._capability_for(intent, parameters.temperature)
        if capability is None:
            return CommandResult.needs_clarification(
                ClarificationReason.MISSING_CAPABILITY,
                intent=intent.value,
                temperature=parameters.temperature,
            )
        scenario = await self._create_scenario.execute(
            CreateScenarioCommand(
                delay_minutes=parameters.duration_minutes,
                target_temperature=parameters.temperature,
                capability=capability,
                target=parameters.target,
            )
        )
        return CommandResult(
            status=OperationStatus.SUCCESS,
            intent=intent.value,
            scenario_id=scenario.id,
            details={"temperature": parameters.temperature},
        )

    async def _capability_for(
        self, intent: Intent, temperature: float | None
    ) -> Capability | None:
        if intent is Intent.COOL:
            return Capability.COOL
        if intent is Intent.HEAT:
            return Capability.HEAT
        if temperature is None:
            return None
        snapshot = await self._get_home_snapshot.execute()
        current = snapshot.reading.temperature
        return capability_for_target(None if current is None else current.celsius, temperature)

    async def _describe_state(self) -> CommandResult:
        snapshot = await self._get_home_snapshot.execute()
        details = {
            "esp_online": snapshot.esp_online,
            "manual_override": snapshot.manual_override,
            "automation": snapshot.automation,
            "active_scenarios": [scenario.id for scenario in snapshot.active_scenarios],
        }
        return CommandResult(
            status=OperationStatus.SUCCESS, intent=Intent.GET_STATUS.value, details=details
        )

    async def _describe_temperature(self) -> CommandResult:
        reading = (await self._get_home_snapshot.execute()).reading.temperature
        return CommandResult(
            status=OperationStatus.SUCCESS,
            intent=Intent.GET_TEMPERATURE.value,
            details={"temperature": None if reading is None else reading.celsius},
        )

    async def _describe_humidity(self) -> CommandResult:
        reading = (await self._get_home_snapshot.execute()).reading.humidity
        return CommandResult(
            status=OperationStatus.SUCCESS,
            intent=Intent.GET_HUMIDITY.value,
            details={"humidity": None if reading is None else reading.percent},
        )

    async def _cancel_latest_scenario(self) -> CommandResult:
        active = await self._get_active_scenarios.execute()
        if not active:
            return CommandResult(
                status=OperationStatus.NOT_FOUND, intent=Intent.CANCEL_SCENARIO.value
            )
        status, scenario = await self._cancel_scenario.execute(active[0].id)
        return CommandResult(
            status=status,
            intent=Intent.CANCEL_SCENARIO.value,
            scenario_id=None if scenario is None else scenario.id,
        )
