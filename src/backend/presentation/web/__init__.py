"""Serving of the built web interface."""

from backend.presentation.web.frontend import mount_frontend, resolve_dist

__all__ = ["mount_frontend", "resolve_dist"]
