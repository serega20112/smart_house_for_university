"""Application configuration assembled from environment variables.

Every value is produced by a pure loader from :mod:`smart_home_backend.config.sections`,
so re-importing this module recomputes the configuration from the current
environment. The module exports a ready-to-use :data:`settings` object, which is
the only supported way to read configuration in the rest of the application.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from smart_home_backend.config.sections import automation, database, esp, nlp, server, telegram

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = "smart-home-backend"

    log_level: str = server.log_level()
    host: str = server.app_host()
    port: int = server.app_port()
    cors_allowed_origins: list[str] = server.cors_allowed_origins()

    database_url: str = database.database_url()
    database_echo: bool = database.database_echo()

    esp_server_host: str = esp.server_host()
    esp_server_port: int = esp.server_port()
    esp_server_path: str = esp.server_path()
    esp_command_timeout_sec: float = esp.command_timeout_sec()
    esp_watchdog_sec: float = esp.watchdog_sec()

    telegram_bot_token: str = telegram.bot_token()
    telegram_chat_id: str = telegram.chat_id()
    telegram_enabled: bool = telegram.enabled()

    automation_interval_sec: float = automation.interval_sec()
    scenario_tick_sec: float = automation.scenario_tick_sec()
    manual_override_minutes: int = automation.manual_override_minutes()
    scenario_summary_minutes: int = automation.scenario_summary_minutes()

    nlp_model_name: str = nlp.model_name()
    nlp_device: str = nlp.device()
    nlp_confidence_threshold: float = nlp.confidence_threshold()
    nlp_allow_lexical_fallback: bool = nlp.allow_lexical_fallback()

    @property
    def telegram_active(self) -> bool:
        """Return whether the Telegram bot is configured and enabled.

        Returns:
            bool: True when the bot can be started.
        """
        return self.telegram_enabled and bool(self.telegram_bot_token)


settings = Settings()
