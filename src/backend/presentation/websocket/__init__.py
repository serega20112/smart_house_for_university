"""События в реальном времени для веб-клиента."""

from backend.presentation.websocket.endpoint import router
from backend.presentation.websocket.hub import WebSocketHub

__all__ = ["WebSocketHub", "router"]
