"""Ports of everything that publishes facts about a home.

Two different things reach the outside world and they are kept apart on purpose:
the realtime stream feeds open browser sockets, and notifications reach a person
through a channel of their choice. Neither is a database write, and neither is a
side effect a use case performs by hand.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Protocol

from smart_home.domain.identifiers import UserId


class DomainEventDispatcher(Protocol):
    """Hands recorded domain facts to whatever is subscribed to them."""

    async def dispatch(self, events: Sequence[object]) -> None:
        """Announce facts an aggregate recorded while it was changing.

        Dispatch happens after the transaction committed, so a subscriber never
        announces something that was rolled back.

        Args:
            events: Facts recorded since the last dispatch.

        Returns:
            None.
        """


class RealtimePublisher(ABC):
    """Broadcasts an event to whoever is watching a home right now."""

    @abstractmethod
    async def publish(self, user_id: UserId, event: str, payload: dict[str, Any]) -> None:
        """Send an event to the clients of one account.

        Args:
            user_id: Owner the event belongs to.
            event: Stable machine readable event name.
            payload: JSON serializable event data.

        Returns:
            None.
        """

    @abstractmethod
    async def broadcast(self, event: str, payload: dict[str, Any]) -> None:
        """Send an event to every connected client.

        A board that nobody owns yet is exactly that kind of fact: it belongs to no
        account, so it is announced to whoever happens to be looking instead of
        being fanned out account by account by the caller.

        Args:
            event: Stable machine readable event name.
            payload: JSON serializable event data.

        Returns:
            None.
        """


class Notification(ABC):
    """Something worth telling a person about."""

    @property
    @abstractmethod
    def text(self) -> str:
        """Return the message as it reaches the person.

        Returns:
            str: Rendered message.
        """

    @property
    @abstractmethod
    def severity(self) -> str:
        """Return how urgent the message is.

        Returns:
            str: One of the severities the channels understand.
        """


class UserNotifier(ABC):
    """Delivers a notification to the owner of a home."""

    @abstractmethod
    async def notify(self, user_id: UserId, notification: Notification) -> None:
        """Send a notification to the owner of a home.

        A channel that is down must not break the business operation that produced
        the notification, so implementations report failures and carry on.

        Args:
            user_id: Owner the notification is about.
            notification: Message to deliver.

        Returns:
            None.
        """


class NotificationFactory(Protocol):
    """Builds the wording of every message a person may receive.

    The vocabulary of the messages belongs to presentation, which is the only layer
    that knows how a person should be addressed and in which language. The
    application decides when a message is due and asks for it by name, so no string
    is ever written inside a use case.
    """

    def board_online(self) -> Notification:
        """Return the message shown when a board comes back.

        Returns:
            Notification: Message to deliver.
        """

    def board_offline(self) -> Notification:
        """Return the message shown when a board goes away.

        Returns:
            Notification: Message to deliver.
        """

    def scenario_started(self, scenario_id: str, target: str | None) -> Notification:
        """Return the message shown when a scenario begins acting.

        Args:
            scenario_id: Identifier of the scenario.
            target: Area or object the user named.

        Returns:
            Notification: Message to deliver.
        """

    def scenario_progress(self, scenario_id: str, temperature: float | None) -> Notification:
        """Return the periodic progress message of a running scenario.

        Args:
            scenario_id: Identifier of the scenario.
            temperature: Current temperature or None.

        Returns:
            Notification: Message to deliver.
        """

    def scenario_finished(self, scenario_id: str, reason: str) -> Notification:
        """Return the message shown when a scenario reaches a final stage.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it reached that stage.

        Returns:
            Notification: Message to deliver.
        """

    def scenario_failed(self, scenario_id: str, reason: str) -> Notification:
        """Return the message shown when a scenario could not be carried out.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it failed.

        Returns:
            Notification: Message to deliver.
        """
