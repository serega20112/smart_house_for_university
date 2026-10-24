"""Кто живёт в состоянии запущенного приложения.

Единственная точка, где презентационный слой что-то кладёт в `app.state` и откуда
это достаёт: вне этого модуля имя атрибута состояния не придумывают, а
список тех, кто переживает вместе с процессом от запуска до остановки, виден в
одном месте.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.applications import Starlette

from backend.application.interface.services.session_token_issuer import SessionTokenIssuer

if TYPE_CHECKING:
    from backend.presentation.websocket.hub import WebSocketHub

HUB_ATTRIBUTE = "hub"
TOKENS_ATTRIBUTE = "tokens"


class StateNotBoundError(RuntimeError):
    """Приложение ещё не сообщило состоянию о том, кого создало на старте."""


def bind(app: Starlette, *, hub: WebSocketHub, tokens: SessionTokenIssuer) -> None:
    """Кладёт в состояние приложения тех, кто живёт вместе с процессом.

    Args:
        app: Запускаемое приложение.
        hub: Концентратор событий реального времени.
        tokens: Тот, кто разбирает токены сессии.
    """
    setattr(app.state, HUB_ATTRIBUTE, hub)
    setattr(app.state, TOKENS_ATTRIBUTE, tokens)


def hub_of(app: Starlette) -> WebSocketHub:
    """Возвращает концентратор, которому этот процесс раздаёт события."""
    return _require[WebSocketHub](app, HUB_ATTRIBUTE)


def tokens_of(app: Starlette) -> SessionTokenIssuer:
    """Возвращает того, кто разбирает предъявленный токен сессии."""
    return _require[SessionTokenIssuer](app, TOKENS_ATTRIBUTE)


def _require[Needed](app: Starlette, name: str) -> Needed:
    """Достаёт один атрибут состояния, отказав, если его ещё не связали."""
    value = getattr(app.state, name, None)
    if value is None:
        raise StateNotBoundError(f"the application was never told about {name!r}")
    return value
