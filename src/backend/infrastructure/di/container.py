"""Building the container.

The composition root does two things and nothing else: it decides which
configuration the process runs with, and it decides which of the presentation
supplied collaborators are in play. Everything else is declared by the providers
of this package.

Two of the context values are adapters the application layer declares but only
presentation can implement: the wording of a notification and the wording of a
spoken answer. Passing them in is the whole interface between the layers.
"""

from __future__ import annotations

from dishka import AsyncContainer, make_async_container

from backend.application.ports.events import Notification, NotificationFactory
from backend.application.ports.voice import ReplyComposer
from backend.config.settings import Settings
from backend.infrastructure.di.providers import (
    APP,
    REQUEST,
    ApplicationProvider,
    BoardProvider,
    CoreProvider,
    DomainProvider,
    LanguageProvider,
    PersistenceProvider,
    TelegramProvider,
    UseCaseProvider,
    VoiceProvider,
    VolatileStateProvider,
)

Container = AsyncContainer

PROVIDERS = (
    CoreProvider(),
    PersistenceProvider(),
    VolatileStateProvider(),
    TelegramProvider(),
    LanguageProvider(),
    VoiceProvider(),
    DomainProvider(),
    BoardProvider(),
    ApplicationProvider(),
    UseCaseProvider(),
)

__all__ = [
    "APP",
    "REQUEST",
    "Container",
    "make_container",
]


class SilentNotificationFactory(NotificationFactory):
    """Placeholder used when the deployment wires no wording at all.

    Presentation owns every sentence a person reads, so the container refuses to
    invent one. A deployment that leaves the factory out produces empty
    notifications instead of a message nobody wrote.

    Args:
        None.

    Returns:
        None.
    """

    def board_online(self) -> Notification:
        """Return the message shown when a board comes back.

        Returns:
            Notification: Empty message.
        """
        return SilentNotification("")

    def board_offline(self) -> Notification:
        """Return the message shown when a board goes away.

        Returns:
            Notification: Empty message.
        """
        return SilentNotification("")

    def scenario_started(self, scenario_id: str, target: str | None) -> Notification:
        """Return the message shown when a scenario begins acting.

        Args:
            scenario_id: Identifier of the scenario.
            target: Area or object the user named.

        Returns:
            Notification: Empty message.
        """
        del scenario_id, target
        return SilentNotification("")

    def scenario_progress(self, scenario_id: str, temperature: float | None) -> Notification:
        """Return the periodic progress message of a running scenario.

        Args:
            scenario_id: Identifier of the scenario.
            temperature: Current temperature or None.

        Returns:
            Notification: Empty message.
        """
        del scenario_id, temperature
        return SilentNotification("")

    def scenario_finished(self, scenario_id: str, reason: str) -> Notification:
        """Return the message shown when a scenario reaches a final stage.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it reached that stage.

        Returns:
            Notification: Empty message.
        """
        del scenario_id, reason
        return SilentNotification("")

    def scenario_failed(self, scenario_id: str, reason: str) -> Notification:
        """Return the message shown when a scenario could not be carried out.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it failed.

        Returns:
            Notification: Empty message.
        """
        del scenario_id, reason
        return SilentNotification("")


class SilentNotification(Notification):
    """A message with no wording behind it.

    Args:
        text: Empty text.

    Returns:
        None.
    """

    def __init__(self, text: str) -> None:
        """Initialize the notification.

        Args:
            text: Empty text.

        Returns:
            None.
        """
        self._text = text

    @property
    def text(self) -> str:
        """Return the message as it reaches the person.

        Returns:
            str: Empty message.
        """
        return self._text

    @property
    def severity(self) -> str:
        """Return how urgent the message is.

        Returns:
            str: Informational severity.
        """
        return "info"


class SilentReplyComposer(ReplyComposer):
    """Placeholder used when the deployment wires no wording at all.

    Args:
        None.

    Returns:
        None.
    """

    def for_result(self, result: object) -> str:
        """Return what to say after a command was carried out.

        Args:
            result: Structured result of the command.

        Returns:
            str: Empty phrase.
        """
        del result
        return ""

    def for_missing_speech(self) -> str:
        """Return what to say when nothing was recognized.

        Returns:
            str: Empty phrase.
        """
        return ""

    def for_unavailable_service(self) -> str:
        """Return what to say when a speech service is down.

        Returns:
            str: Empty phrase.
        """
        return ""


def make_container(
    settings: Settings,
    *,
    notifications: NotificationFactory | None = None,
    composer: ReplyComposer | None = None,
) -> Container:
    """Build the dependency graph of one process.

    Args:
        settings: Configuration the graph is built from.
        notifications: Builds the wording of every message a person receives.
            Presentation owns it, so the caller supplies it; without one the
            notifications carry no wording instead of inventing some here.
        composer: Builds the wording of a spoken answer, for the same reason.

    Returns:
        Container: Container holding everything the process needs.
    """
    context = {
        Settings: settings,
        NotificationFactory: notifications or SilentNotificationFactory(),
        ReplyComposer: composer or SilentReplyComposer(),
    }
    return make_async_container(*PROVIDERS, context=context)
