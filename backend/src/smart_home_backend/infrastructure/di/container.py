"""Composition root building the whole object graph.

This is the only place where the layers are wired together: ports get their
adapters, the engines get their collaborators and every use case gets its
dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWork
from smart_home_backend.application.services import (
    AutomationEngine,
    BackgroundScheduler,
    CommandInterpreter,
    DeviceExecutor,
    HomeRuntime,
    HomeStateSynchronizer,
    ScenarioEngine,
)
from smart_home_backend.application.use_cases import (
    CancelScenarioUseCase,
    CreateDeviceUseCase,
    CreateScenarioUseCase,
    DeleteDeviceUseCase,
    GetActiveScenariosUseCase,
    GetAutomationSettingsUseCase,
    GetDeviceUseCase,
    GetDevicesUseCase,
    GetHomeSnapshotUseCase,
    ProcessUserCommandUseCase,
    RunAutomationCycleUseCase,
    RunClimateCapabilityUseCase,
    SetDeviceModeUseCase,
    SetTargetHumidityUseCase,
    SetTargetTemperatureUseCase,
    TickScenariosUseCase,
    ToggleAutomationUseCase,
    TurnAllDevicesUseCase,
    TurnDeviceOffUseCase,
    TurnDeviceOnUseCase,
    UpdateAutomationUseCase,
    UpdateDeviceUseCase,
)
from smart_home_backend.config import Settings
from smart_home_backend.infrastructure.clock import SystemClock
from smart_home_backend.infrastructure.database import (
    SqlUnitOfWork,
    build_engine,
    build_session_factory,
)
from smart_home_backend.infrastructure.esp import EspConnection, EspGatewayAdapter
from smart_home_backend.infrastructure.nlp import build_command_parser, build_intent_classifier
from smart_home_backend.infrastructure.telegram import TelegramNotifier


@dataclass
class Container:
    """Assembled dependency graph of the application.

    Args:
        settings: Configuration the graph was built from.
        engine: Async database engine.
        uow_factory: Factory producing units of work.
        runtime: Live state of the home.
        esp_connection: Board WebSocket transport.
        esp_gateway: Hardware gateway used by the application.
        synchronizer: Inbound board data handler.
        scheduler: Background business loops.
        turn_device_on: Device command.
        turn_device_off: Device command.
        set_device_mode: Device command.
        turn_all_devices: Device command.
        create_device: Device configuration command.
        update_device: Device configuration command.
        delete_device: Device configuration command.
        set_target_temperature: Climate target command.
        set_target_humidity: Climate target command.
        run_climate_capability: Climate capability command.
        update_automation: Automation configuration command.
        toggle_automation: Automation mode switch.
        run_automation_cycle: One automation cycle.
        create_scenario: Scenario command.
        cancel_scenario: Scenario command.
        tick_scenarios: Scenario tick.
        process_user_command: Free-form command entry point.
        get_devices: Read side.
        get_device: Read side.
        get_automation_settings: Read side.
        get_active_scenarios: Read side.
        get_home_snapshot: Read side.

    Returns:
        None.
    """

    settings: Settings
    engine: Any
    uow_factory: Any
    runtime: HomeRuntime
    esp_connection: EspConnection
    esp_gateway: EspGatewayAdapter
    synchronizer: HomeStateSynchronizer
    scheduler: BackgroundScheduler
    turn_device_on: TurnDeviceOnUseCase
    turn_device_off: TurnDeviceOffUseCase
    set_device_mode: SetDeviceModeUseCase
    turn_all_devices: TurnAllDevicesUseCase
    create_device: CreateDeviceUseCase
    update_device: UpdateDeviceUseCase
    delete_device: DeleteDeviceUseCase
    set_target_temperature: SetTargetTemperatureUseCase
    set_target_humidity: SetTargetHumidityUseCase
    run_climate_capability: RunClimateCapabilityUseCase
    update_automation: UpdateAutomationUseCase
    toggle_automation: ToggleAutomationUseCase
    run_automation_cycle: RunAutomationCycleUseCase
    create_scenario: CreateScenarioUseCase
    cancel_scenario: CancelScenarioUseCase
    tick_scenarios: TickScenariosUseCase
    process_user_command: ProcessUserCommandUseCase
    get_devices: GetDevicesUseCase
    get_device: GetDeviceUseCase
    get_automation_settings: GetAutomationSettingsUseCase
    get_active_scenarios: GetActiveScenariosUseCase
    get_home_snapshot: GetHomeSnapshotUseCase


def build_container(settings: Settings, events: EventBus) -> Container:
    """Build every adapter, engine and use case of the application.

    Args:
        settings: Application configuration.
        events: Event bus provided by the presentation layer.

    Returns:
        Container: Assembled dependency graph.
    """
    engine = build_engine(settings.database_url, echo=settings.database_echo)
    session_factory = build_session_factory(engine)

    def uow_factory() -> UnitOfWork:
        return SqlUnitOfWork(session_factory)

    clock = SystemClock()
    runtime = HomeRuntime(clock)

    esp_connection = EspConnection(
        host=settings.esp_server_host,
        port=settings.esp_server_port,
        path=settings.esp_server_path,
        handler_provider=lambda: synchronizer,
        command_timeout=settings.esp_command_timeout_sec,
    )
    esp_gateway = EspGatewayAdapter(esp_connection)
    notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id
    )
    synchronizer = HomeStateSynchronizer(
        runtime=runtime,
        events=events,
        notifier=notifier,
        uow_factory=uow_factory,
        esp=esp_gateway,
    )

    executor = DeviceExecutor(esp=esp_gateway, runtime=runtime, events=events)
    automation_engine = AutomationEngine(runtime=runtime, executor=executor)
    scenario_engine = ScenarioEngine(
        runtime=runtime,
        executor=executor,
        events=events,
        notifier=notifier,
        clock=clock,
        manual_override_minutes=settings.manual_override_minutes,
        summary_minutes=settings.scenario_summary_minutes,
    )

    override_minutes = settings.manual_override_minutes
    turn_device_on = TurnDeviceOnUseCase(uow_factory, executor, runtime, override_minutes)
    turn_device_off = TurnDeviceOffUseCase(uow_factory, executor, runtime, override_minutes)
    set_device_mode = SetDeviceModeUseCase(uow_factory, executor, runtime, override_minutes)
    turn_all_devices = TurnAllDevicesUseCase(uow_factory, executor, runtime, override_minutes)

    create_device = CreateDeviceUseCase(uow_factory, events)
    update_device = UpdateDeviceUseCase(uow_factory, events)
    delete_device = DeleteDeviceUseCase(uow_factory, events, runtime)

    set_target_temperature = SetTargetTemperatureUseCase(uow_factory, events)
    set_target_humidity = SetTargetHumidityUseCase(uow_factory, events)
    run_climate_capability = RunClimateCapabilityUseCase(
        uow_factory, executor, runtime, override_minutes
    )

    update_automation = UpdateAutomationUseCase(uow_factory, events)
    toggle_automation = ToggleAutomationUseCase(uow_factory, events)
    run_automation_cycle = RunAutomationCycleUseCase(uow_factory, automation_engine)

    create_scenario = CreateScenarioUseCase(uow_factory, scenario_engine)
    cancel_scenario = CancelScenarioUseCase(uow_factory)
    tick_scenarios = TickScenariosUseCase(uow_factory, scenario_engine)

    get_devices = GetDevicesUseCase(uow_factory)
    get_device = GetDeviceUseCase(uow_factory)
    get_automation_settings = GetAutomationSettingsUseCase(uow_factory)
    get_active_scenarios = GetActiveScenariosUseCase(uow_factory)
    get_home_snapshot = GetHomeSnapshotUseCase(uow_factory, runtime)

    interpreter = CommandInterpreter(
        classifier=build_intent_classifier(settings),
        parser=build_command_parser(),
        confidence_threshold=settings.nlp_confidence_threshold,
    )
    process_user_command = ProcessUserCommandUseCase(
        interpreter=interpreter,
        uow_factory=uow_factory,
        get_home_snapshot=get_home_snapshot,
        get_active_scenarios=get_active_scenarios,
        turn_device_on=turn_device_on,
        turn_device_off=turn_device_off,
        set_device_mode=set_device_mode,
        turn_all_devices=turn_all_devices,
        set_target_temperature=set_target_temperature,
        set_target_humidity=set_target_humidity,
        run_climate_capability=run_climate_capability,
        create_scenario=create_scenario,
        cancel_scenario=cancel_scenario,
    )

    scheduler = BackgroundScheduler(
        run_automation=run_automation_cycle,
        tick_scenarios=tick_scenarios,
        automation_interval=settings.automation_interval_sec,
        scenario_interval=settings.scenario_tick_sec,
    )

    return Container(
        settings=settings,
        engine=engine,
        uow_factory=uow_factory,
        runtime=runtime,
        esp_connection=esp_connection,
        esp_gateway=esp_gateway,
        synchronizer=synchronizer,
        scheduler=scheduler,
        turn_device_on=turn_device_on,
        turn_device_off=turn_device_off,
        set_device_mode=set_device_mode,
        turn_all_devices=turn_all_devices,
        create_device=create_device,
        update_device=update_device,
        delete_device=delete_device,
        set_target_temperature=set_target_temperature,
        set_target_humidity=set_target_humidity,
        run_climate_capability=run_climate_capability,
        update_automation=update_automation,
        toggle_automation=toggle_automation,
        run_automation_cycle=run_automation_cycle,
        create_scenario=create_scenario,
        cancel_scenario=cancel_scenario,
        tick_scenarios=tick_scenarios,
        process_user_command=process_user_command,
        get_devices=get_devices,
        get_device=get_device,
        get_automation_settings=get_automation_settings,
        get_active_scenarios=get_active_scenarios,
        get_home_snapshot=get_home_snapshot,
    )
