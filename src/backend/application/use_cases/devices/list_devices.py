"""Список устройств аккаунта с их живым состоянием."""

from __future__ import annotations

from backend.application.interfaces.queries.device_queries import DeviceQueries
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.domain.identifiers import UserId
from backend.domain.value_objects.devices.device_view import DeviceView


class ListDevicesUseCase:
    """Показывает устройства так, какие они сейчас."""

    def __init__(self, queries: DeviceQueries, state_store: HomeStateStore) -> None:
        """Собирает сценарий списка устройств.

        Args:
            queries: Чтения конфигурации устройств.
            state_store: Хранилище изменчивого состояния дома.
        """
        self._queries = queries
        self._state_store = state_store

    async def execute(self, user_id: UserId) -> list[DeviceView]:
        """Возвращает все устройства аккаунта.

        Состояние берётся из хранилища изменчивого состояния, а не угадывается:
        устройство без подтверждения платы остаётся таким, каким его видят.

        Args:
            user_id: Владелец устройств.

        Returns:
            list[DeviceView]: Устройства с их живым состоянием.
        """
        devices = await self._queries.list_all(user_id)
        state = await self._state_store.read(user_id)
        return [
            device.with_status(state.status_for(device.id, device.channel)) for device in devices
        ]
