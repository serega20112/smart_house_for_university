"""Application configuration package.

Re-exports the settings singleton so consumers can use
``from smart_home_backend.config import settings``.
"""

from smart_home_backend.config.settings import Settings, settings

__all__ = ["Settings", "settings"]
