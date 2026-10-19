"""Application configuration.

Every value arrives from the environment through ``pydantic-settings``. Sections are
real objects, so a setting reads as ``settings.board.command_timeout_sec`` instead of
a flat field named after a whole sentence. A malformed value, a missing secret or a
number outside its range stops the process at construction time with a report naming
the offending variable, instead of surfacing hours later as a ``ValueError`` raised
from somewhere deep inside a request.

The object is built by the composition root and injected from there, so nothing
imports a ready made instance and a test may hand the application any configuration it
likes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class _Section(BaseSettings):
    """Common behaviour of every configuration section.

    Sections read their own prefixed variables from the environment and from the
    dotenv file, which keeps the flat variable namespace of a deployment while the
    application sees nested objects.

    Args:
        None.

    Returns:
        None.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ServerSettings(_Section):
    """Address, logging and browser access of the HTTP server."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=ENV_FILE, extra="ignore")

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        """Accept a comma separated origin list as a single environment value.

        Args:
            value: Raw value taken from the environment.

        Returns:
            object: List of origins, or the original value when it is already one.
        """
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


class AuthSettings(_Section):
    """Session token signing and lifetime."""

    model_config = SettingsConfigDict(env_prefix="AUTH_", env_file=ENV_FILE, extra="ignore")

    token_secret: str = Field(min_length=32)
    session_lifetime_minutes: int = Field(default=720, ge=5, le=525600)


class DatabaseSettings(_Section):
    """Connection to the relational store."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_", env_file=ENV_FILE, extra="ignore")

    url: PostgresDsn = "postgresql+asyncpg://smart_home:smart_home@localhost:5432/smart_home"
    echo: bool = False
    pool_size: int = Field(default=10, ge=1, le=100)
    pool_max_overflow: int = Field(default=10, ge=0, le=100)
    pool_recycle_sec: int = Field(default=1800, ge=60, le=86400)


class RedisSettings(_Section):
    """Connection to the store holding volatile and shared state."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file=ENV_FILE, extra="ignore")

    url: str = "redis://localhost:6379/0"
    password: str | None = None
    key_prefix: str = "smart-home"


class BoardSettings(_Section):
    """WebSocket transport the boards dial in to."""

    model_config = SettingsConfigDict(env_prefix="BOARD_", env_file=ENV_FILE, extra="ignore")

    command_timeout_sec: float = Field(default=5.0, gt=0)
    watchdog_sec: float = Field(default=15.0, gt=0)
    claim_ttl_sec: int = Field(default=120, ge=10, le=3600)
    relay_channel_count: int = Field(default=6, ge=1, le=32)


class VoiceSettings(_Section):
    """Remote speech services the board microphone is streamed to."""

    model_config = SettingsConfigDict(env_prefix="VOICE_", env_file=ENV_FILE, extra="ignore")

    enabled: bool = False
    base_url: str = "http://127.0.0.1:8100"
    timeout_sec: float = Field(default=30.0, gt=0)
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    max_audio_sec: int = Field(default=8, ge=1, le=60)
    min_audio_bytes: int = Field(default=8000, ge=256, le=1_000_000)
    synthesis_enabled: bool = True
    vad_threshold: int = Field(default=180, ge=0, le=1023)
    neural_commands: bool = True
    bootstrap_url: str = ""

    @property
    def active(self) -> bool:
        """Return whether a speech service may be called at all.

        Returns:
            bool: True when voice commands are enabled and an address is configured.
        """
        return self.enabled and bool(self.base_url)


class LanguageSettings(_Section):
    """Natural language understanding pipeline."""

    model_config = SettingsConfigDict(env_prefix="LANGUAGE_", env_file=ENV_FILE, extra="ignore")

    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimensions: int = Field(default=384, ge=8, le=4096)
    device: str = "cpu"
    confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)


class TelegramSettings(_Section):
    """Telegram bot delivering notifications and accepting commands."""

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_", env_file=ENV_FILE, extra="ignore")

    enabled: bool = False
    bot_token: str = ""
    notify_chat_id: str = ""

    @property
    def active(self) -> bool:
        """Return whether the bot may be started.

        Returns:
            bool: True when the bot is enabled and a token is configured.
        """
        return self.enabled and bool(self.bot_token)


class AutomationSettings(_Section):
    """Periods of the background business cycles."""

    model_config = SettingsConfigDict(env_prefix="AUTOMATION_", env_file=ENV_FILE, extra="ignore")

    automation_cycle_sec: float = Field(default=10.0, gt=0)
    scenario_tick_sec: float = Field(default=5.0, gt=0)
    manual_override_minutes: int = Field(default=30, ge=0, le=1440)
    scenario_summary_minutes: int = Field(default=10, ge=1, le=1440)
    scenario_summary_ttl_sec: int = Field(default=600, ge=30, le=86400)


class Settings(BaseSettings):
    """Root of the application configuration.

    Attributes:
        app_name: Name reported by the health probe.
        server: HTTP server section.
        auth: Session token section.
        database: Relational store section.
        redis: Volatile and shared state section.
        board: Board transport section.
        voice: Speech services section.
        language: Natural language pipeline section.
        telegram: Bot section.
        automation: Background cycle section.

    Returns:
        None.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = "smart-home-backend"
    server: ServerSettings = Field(default_factory=ServerSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    board: BoardSettings = Field(default_factory=BoardSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    language: LanguageSettings = Field(default_factory=LanguageSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    automation: AutomationSettings = Field(default_factory=AutomationSettings)