"""Presentation layer.

Everything the outside world talks to: the REST API, the realtime WebSocket and
the Telegram bot. This layer maps domain objects onto transport payloads and
holds no business rules.
"""

from smart_home_backend.presentation.app_factory import create_app

__all__ = ["create_app"]
