"""Realtime interface for the web client."""

from backend.presentation.websocket.endpoint import router
from backend.presentation.websocket.hub import WebSocketHub

__all__ = ["WebSocketHub", "router"]
