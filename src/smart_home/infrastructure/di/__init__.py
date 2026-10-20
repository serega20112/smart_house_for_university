"""Dependency injection of the smart home smart_home.

The graph is described by the providers of this package and built by
:func:`make_container`, which returns a Dishka ``AsyncContainer``. A process asks
that container for the things it needs: the board transport and the long lived
adapters straight from the application scope, and one fresh set of use cases from
the request scope.
"""

from smart_home.infrastructure.di.container import (
    APP,
    REQUEST,
    Container,
    SilentNotificationFactory,
    SilentReplyComposer,
    make_container,
)

__all__ = [
    "APP",
    "REQUEST",
    "Container",
    "SilentNotificationFactory",
    "SilentReplyComposer",
    "make_container",
]
