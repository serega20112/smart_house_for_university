"""Команды: то, что человек сказал, превращается в действие дома."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.dto.language.intent import Intent
from backend.application.interfaces.queries.scenario_queries import ScenarioQueries
from backend.application.interfaces.services.language.command_understanding import (
    CommandUnderstandingPort,
)
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.command_dispatcher import CommandDispatcher, CommandHandler
from backend.application.services.device_control import DeviceControlService
from backend.application.services.home_overview import HomeOverviewQuery
from backend.application.use_cases.commands.cancel_scenario import CancelScenarioCommandUseCase
from backend.application.use_cases.commands.describe_home import DescribeHomeCommandUseCase
from backend.application.use_cases.commands.read_humidity import ReadHumidityCommandUseCase
from backend.application.use_cases.commands.read_temperature import (
    ReadTemperatureCommandUseCase,
)
from backend.application.use_cases.commands.run_capability import RunCapabilityCommandUseCase
from backend.application.use_cases.commands.schedule_scenario import ScheduleScenarioCommandUseCase
from backend.application.use_cases.commands.set_humidity_target import (
    SetHumidityTargetCommandUseCase,
)
from backend.application.use_cases.commands.set_temperature_target import (
    SetTemperatureTargetCommandUseCase,
)
from backend.application.use_cases.commands.switch_all import SwitchAllDevicesCommandUseCase
from backend.application.use_cases.commands.switch_device import SwitchDeviceCommandUseCase
from backend.application.use_cases.scenarios.cancel_scenario import CancelScenarioUseCase
from backend.application.use_cases.scenarios.schedule_scenario import ScheduleScenarioUseCase
from backend.domain.policies.climate_policy import DemandCalculator
from backend.domain.policies.device_selector import DeviceSelector

APP = Scope.APP


class CommandsUseCaseProvider(Provider):
    """По одному сценарию на намерение и шина, выбирающая сценарий по нему."""

    @provide(scope=APP)
    def switch_device(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
    ) -> SwitchDeviceCommandUseCase:
        """Собирает переключение одного устройства по фразе."""
        return SwitchDeviceCommandUseCase(home_uow, control, DeviceSelector())

    @provide(scope=APP)
    def switch_all(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
    ) -> SwitchAllDevicesCommandUseCase:
        """Собирает переключение всего дома по фразе."""
        return SwitchAllDevicesCommandUseCase(home_uow, control)

    @provide(scope=APP)
    def set_temperature(
        self, home_uow: HomeUnitOfWorkFactory
    ) -> SetTemperatureTargetCommandUseCase:
        """Собирает цель по температуре по фразе."""
        return SetTemperatureTargetCommandUseCase(home_uow)

    @provide(scope=APP)
    def set_humidity(self, home_uow: HomeUnitOfWorkFactory) -> SetHumidityTargetCommandUseCase:
        """Собирает цель по влажности по фразе."""
        return SetHumidityTargetCommandUseCase(home_uow)

    @provide(scope=APP)
    def run_capability(
        self,
        home_uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
        state_store: HomeStateStore,
    ) -> RunCapabilityCommandUseCase:
        """Собирает выполнение способности по фразе."""
        return RunCapabilityCommandUseCase(home_uow, control, state_store, DemandCalculator())

    @provide(scope=APP)
    def describe_home(self, overview: HomeOverviewQuery) -> DescribeHomeCommandUseCase:
        """Собирает описание дома по фразе."""
        return DescribeHomeCommandUseCase(overview)

    @provide(scope=APP)
    def read_temperature(self, state_store: HomeStateStore) -> ReadTemperatureCommandUseCase:
        """Собирает чтение температуры по фразе."""
        return ReadTemperatureCommandUseCase(state_store)

    @provide(scope=APP)
    def read_humidity(self, state_store: HomeStateStore) -> ReadHumidityCommandUseCase:
        """Собирает чтение влажности по фразе."""
        return ReadHumidityCommandUseCase(state_store)

    @provide(scope=APP)
    def schedule_scenario(
        self, schedule: ScheduleScenarioUseCase
    ) -> ScheduleScenarioCommandUseCase:
        """Собирает отложенное действие по фразе."""
        return ScheduleScenarioCommandUseCase(schedule, DemandCalculator())

    @provide(scope=APP)
    def cancel_scenario(
        self, cancel: CancelScenarioUseCase, scenario_queries: ScenarioQueries
    ) -> CancelScenarioCommandUseCase:
        """Собирает отмену сценария по фразе."""
        return CancelScenarioCommandUseCase(cancel, scenario_queries)

    @provide(scope=APP)
    def dispatcher(
        self,
        understanding: CommandUnderstandingPort,
        switch_device_command: SwitchDeviceCommandUseCase,
        switch_all_command: SwitchAllDevicesCommandUseCase,
        set_temperature_command: SetTemperatureTargetCommandUseCase,
        set_humidity_command: SetHumidityTargetCommandUseCase,
        run_capability_command: RunCapabilityCommandUseCase,
        describe_home_command: DescribeHomeCommandUseCase,
        read_temperature_command: ReadTemperatureCommandUseCase,
        read_humidity_command: ReadHumidityCommandUseCase,
        schedule_scenario_command: ScheduleScenarioCommandUseCase,
        cancel_scenario_command: CancelScenarioCommandUseCase,
    ) -> CommandDispatcher:
        """Собирает шину команд: намерение — сценарий, закрывающий его.

        Реестр живёт здесь одной строкой на намерение, поэтому добавление того, что
        человек может сказать, не правит ни один готовый сценарий.
        """
        handlers: list[tuple[Intent, CommandHandler]] = [
            (Intent.SWITCH_DEVICE, switch_device_command.execute),
            (Intent.SWITCH_ALL, switch_all_command.execute),
            (Intent.SET_TEMPERATURE, set_temperature_command.execute),
            (Intent.SET_HUMIDITY, set_humidity_command.execute),
            (Intent.RUN_CAPABILITY, run_capability_command.execute),
            (Intent.DESCRIBE_HOME, describe_home_command.execute),
            (Intent.READ_TEMPERATURE, read_temperature_command.execute),
            (Intent.READ_HUMIDITY, read_humidity_command.execute),
            (Intent.SCHEDULE_SCENARIO, schedule_scenario_command.execute),
            (Intent.CANCEL_SCENARIO, cancel_scenario_command.execute),
        ]
        return CommandDispatcher(understanding, dict(handlers))
