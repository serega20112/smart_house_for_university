"""Меняет настройку автоматизации одного аккаунта.

Настройка — агрегат, поэтому каждое изменение идёт через его собственные методы, а
сценарий приложения лишь решает, какой из них позвать. Новые значения проверяются до
записи, и отвергнутое изменение оставляет настройку ровно такой, какой она была.
"""

from __future__ import annotations

from backend.application.dto.automation.automation_patch import AutomationPatch
from backend.application.dto.views.automation_view import AutomationView
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.events import EventName
from backend.domain.identifiers import UserId


class UpdateAutomationUseCase:
    """Применяет частичное изменение настройки автоматизации."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
    ) -> None:
        """Инициализирует сценарий.

        Args:
            home_uow: Фабрика транзакций над конфигурацией.
            realtime: Издатель событий в открытые соединения.
            dispatcher: Объявляет факт изменения настройки.
        """
        self._home_uow = home_uow
        self._realtime = realtime
        self._dispatcher = dispatcher

    async def execute(self, user_id: UserId, patch: AutomationPatch) -> AutomationView:
        """Применяет частичное изменение настройки автоматизации.

        Args:
            user_id: Владелец, разрешённый из сессии.
            patch: Поля, которые нужно изменить.

        Returns:
            AutomationView: Настройка такой, какая она теперь.
        """
        async with self._home_uow() as uow:
            settings = await uow.automation.get(user_id)
            if settings is None:
                settings = AutomationSettings.create(user_id)
            _apply(settings, patch)
            await uow.automation.save(settings)
            await uow.commit()
        await self._realtime.publish(user_id, EventName.AUTOMATION_UPDATED, {"updated": True})
        await self._dispatcher.dispatch(settings.pull_events())
        return _view_of(settings)


def _apply(settings: AutomationSettings, patch: AutomationPatch) -> None:
    """Применяет частичное изменение к настройке.

    Args:
        settings: Настройка, которую меняют.
        patch: Поля, которые нужно изменить.
    """
    if patch.enabled is not None:
        if patch.enabled:
            settings.enable()
        else:
            settings.disable()
    if patch.target_temperature is not None or patch.temperature_tolerance is not None:
        settings.aim_at_temperature(
            settings.target_temperature
            if patch.target_temperature is None
            else patch.target_temperature,
            patch.temperature_tolerance,
        )
    if patch.target_humidity is not None or patch.humidity_tolerance is not None:
        settings.aim_at_humidity(
            settings.target_humidity if patch.target_humidity is None else patch.target_humidity,
            patch.humidity_tolerance,
        )
    if patch.participating_device_ids is not None:
        settings.set_participants(patch.participating_device_ids)


def _view_of(settings: AutomationSettings) -> AutomationView:
    """Возвращает настройку в том виде, в каком она нужна интерфейсу.

    Args:
        settings: Настройка аккаунта.

    Returns:
        AutomationView: Настройка, приготовленная для показа.
    """
    return AutomationView(
        enabled=settings.enabled,
        target_temperature=settings.target_temperature.celsius,
        target_humidity=settings.target_humidity.percent,
        temperature_tolerance=settings.temperature_tolerance,
        humidity_tolerance=settings.humidity_tolerance,
        participating_device_ids=settings.participating_device_ids,
    )
