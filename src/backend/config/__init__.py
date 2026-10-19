"""Application configuration package.

The configuration is built explicitly by the composition root and injected, so this
package offers the schema only and never a ready made instance.
"""

from backend.config.settings import (
    AuthSettings,
    AutomationSettings,
    BoardSettings,
    DatabaseSettings,
    LanguageSettings,
    RedisSettings,
    ServerSettings,
    Settings,
    TelegramSettings,
    VoiceSettings,
)

__all__ = [
    "AuthSettings",
    "AutomationSettings",
    "BoardSettings",
    "DatabaseSettings",
    "LanguageSettings",
    "RedisSettings",
    "ServerSettings",
    "Settings",
    "TelegramSettings",
    "VoiceSettings",
]