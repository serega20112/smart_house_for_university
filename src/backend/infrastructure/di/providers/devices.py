"""Устройства: настройка, список и переключение."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interface.queries.device_queries import DeviceQueries
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.application.services.device_control import DeviceControlService
from backend.application.services.reaction_dispatcher import ReactionDispatcher
from backend.application.use_cases.devices.create_device import CreateDeviceUseCase
from backend.application.use_cases.devices.delete_device import DeleteDeviceUseCase
from backend.application.use_cases.devices.list_devices import ListDevicesUseCase
from backend.application.use_cases.devices.switch_all_devices import SwitchAllDevicesUseCase
from backend.application.use_cases.devices.switch_device import SwitchDeviceUseCase
from backend.application.use_cases.devices.update_device import UpdateDeviceUseCase
from backend.config.settings import Settings

REQUEST = Scope.REQUEST


class DeviceProvider(Provider):
    """Всё, что интерфейс делает с логическими устройствами дома."""

    @provide(scope=REQUEST)
    def create_device(
        self,
        uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        reactions: ReactionDispatcher,
        state_store: HomeStateStore,
    ) -> CreateDeviceUseCase:
        """Собирает создание устройства."""
        return CreateDeviceUseCase(uow, realtime, reactions, state_store)

    @provide(scope=REQUEST)
    def update_device(
        self,
        uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        reactions: ReactionDispatcher,
        state_store: HomeStateStore,
        settings: Settings,
    ) -> UpdateDeviceUseCase:
        """Собирает изменение устройства."""
        return UpdateDeviceUseCase(
            uow,
            realtime,
            reactions,
            state_store,
            refresh_attempts=settings.device_refresh_attempts,
        )

    @provide(scope=REQUEST)
    def delete_device(
        self,
        uow: HomeUnitOfWorkFactory,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
    ) -> DeleteDeviceUseCase:
        """Собирает удаление устройства."""
        return DeleteDeviceUseCase(uow, state_store, realtime)

    @provide(scope=REQUEST)
    def list_devices(
        self, queries: DeviceQueries, state_store: HomeStateStore
    ) -> ListDevicesUseCase:
        """Собирает список устройств с их живым состоянием."""
        return ListDevicesUseCase(queries, state_store)

    @provide(scope=REQUEST)
    def switch_device(self, control: DeviceControlService) -> SwitchDeviceUseCase:
        """Собирает переключение одного устройства."""
        return SwitchDeviceUseCase(control)

    @provide(scope=REQUEST)
    def switch_all_devices(
        self,
        uow: HomeUnitOfWorkFactory,
        control: DeviceControlService,
    ) -> SwitchAllDevicesUseCase:
        """Собирает переключение всех устройств дома."""
        return SwitchAllDevicesUseCase(uow, control)
