"""Access to the assembled dependency graph from the routes."""

from __future__ import annotations

from fastapi import Request

from backend.infrastructure.di import Container


def get_container(request: Request) -> Container:
    """Return the dependency graph stored on the application.

    Args:
        request: Incoming request.

    Returns:
        Container: Assembled dependency graph.
    """
    return request.app.state.container
