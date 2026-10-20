"""Realtime interface for the web client."""

from smart_home.presentation.websocket.endpoint import router
from smart_home.presentation.websocket.hub import WebSocketHub

__all__ = ["WebSocketHub", "router"]
