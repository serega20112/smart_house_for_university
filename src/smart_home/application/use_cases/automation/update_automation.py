"""Change the automation configuration of one account.

The configuration is an aggregate, so every change goes through its own methods
and the use case only decides which of them to call. The new values are validated
before they are stored, and a refused change leaves the configuration exactly as
it was.
"""

from __future__ import annotations

from smart_home.application.dto.automation import AutomationPatch, AutomationView
from smart_home.application.ports.events import DomainEventDispatcher, RealtimePublisher
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from smart_home.domain.climate.automation_settings import AutomationSettings
from smart_home.domain.identifiers import UserId

AUTOMATION_UPDATED_EVENT = "automation.updated"


class UpdateAutomationUseCase:
    """Applies a partial change to the automation configuration."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
    ) -> None:
        """Initialize the use case.

        Args:
            home_uow: Factory producing transactions over the configuration.
            realtime: Publisher of events to the open clients.
            dispatcher: Announces the fact that the configuration changed.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._realtime = realtime
        self._dispatcher = dispatcher

    async def execute(self, user_id: UserId, patch: AutomationPatch) -> AutomationView:
        """Apply a partial change to the automation configuration.

        Args:
            user_id: Owner resolved from the session.
            patch: Fields to change.

        Returns:
            AutomationView: The configuration as it is now.
        """
        async with self._home_uow() as uow:
            settings = await uow.automation.get(user_id)
            if settings is None:
                settings = AutomationSettings.create(user_id)
            _apply(settings, patch)
            await uow.automation.save(settings)
        await self._realtime.publish(user_id, AUTOMATION_UPDATED_EVENT, {"updated": True})
        await self._dispatcher.dispatch(settings.pull_events())
        return _view_of(settings)


def _apply(settings: AutomationSettings, patch: AutomationPatch) -> None:
    """Apply a partial change to the configuration.

    Args:
        settings: Configuration to change.
        patch: Fields to change.

    Returns:
        None.
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
    """Return the configuration as the interface needs it.

    Args:
        settings: Configuration of the account.

    Returns:
        AutomationView: Configuration shaped for display.
    """
    return AutomationView(
        enabled=settings.enabled,
        target_temperature=settings.target_temperature.celsius,
        target_humidity=settings.target_humidity.percent,
        temperature_tolerance=settings.temperature_tolerance,
        humidity_tolerance=settings.humidity_tolerance,
        participating_device_ids=settings.participating_device_ids,
    )
