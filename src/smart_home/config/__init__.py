"""Application configuration package.

The configuration is built explicitly by the composition root and injected, so this
package offers the schema only and never a ready made instance.
"""

from smart_home.config.settings import (
    AuthSettings,
    AutomationTimings,
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
    "AutomationTimings",
    "BoardSettings",
    "DatabaseSettings",
    "LanguageSettings",
    "RedisSettings",
    "ServerSettings",
    "Settings",
    "TelegramSettings",
    "VoiceSettings",
]
