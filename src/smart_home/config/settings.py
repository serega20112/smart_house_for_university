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
from typing import Annotated, Final

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
"""Root of the repository, where the dotenv file of a checkout lives."""

ENV_FILE: Final[Path] = PROJECT_ROOT / ".env"
"""Dotenv file read by every section of the configuration."""


class _Section(BaseSettings):
    """Common behaviour of every configuration section.

    Sections read their own prefixed variables from the environment and from the
    dotenv file, which keeps the flat variable namespace of a deployment while the
    application sees nested objects.

    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )


class ServerSettings(_Section):
    """Address, logging and browser access of the HTTP server.

    Attributes:
        host: Address the HTTP server binds to.
        port: Port the HTTP server listens on.
        log_level: Minimum level every record is rendered at.
        cors_allowed_origins: Origins allowed to call the API. An empty list
            switches cross origin access off entirely.
    """

    model_config = SettingsConfigDict(env_prefix="APP_")

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
    """Session token signing and lifetime.

    Attributes:
        token_secret: Secret the session tokens are signed with.
        session_lifetime_minutes: How long a session stays valid.
    """

    model_config = SettingsConfigDict(env_prefix="AUTH_")

    token_secret: SecretStr = Field(min_length=32)
    session_lifetime_minutes: int = Field(default=720, ge=5, le=525600)


class DatabaseSettings(_Section):
    """Connection to the relational store.

    Attributes:
        url: Connection string of the relational store.
        echo: Whether the statements are logged.
        pool_size: Number of connections kept open.
        pool_max_overflow: Connections opened above the pool size.
        pool_recycle_sec: Lifetime of a pooled connection.
    """

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: PostgresDsn = "postgresql+asyncpg://smart_home:smart_home@localhost:5432/smart_home"
    echo: bool = False
    pool_size: int = Field(default=10, ge=1, le=100)
    pool_max_overflow: int = Field(default=10, ge=0, le=100)
    pool_recycle_sec: int = Field(default=1800, ge=60, le=86400)


class RedisSettings(_Section):
    """Connection to the store holding volatile and shared state.

    Attributes:
        url: Connection string of the store.
        password: Password of the store, when it asks for one.
        key_prefix: Prefix every key of this deployment carries.
    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"
    password: SecretStr | None = None
    key_prefix: str = "smart-home"


class BoardSettings(_Section):
    """WebSocket transport the boards dial in to.

    Attributes:
        socket_port: Port the board transport listens on.
        socket_path: Path of the board transport.
        command_timeout_sec: How long a board has to confirm a command.
        watchdog_sec: How long a board may stay silent before it is unavailable.
        claim_ttl_sec: How long an announced board stays open for taking.
    """

    model_config = SettingsConfigDict(env_prefix="BOARD_")

    socket_port: int = Field(default=8001, ge=1, le=65535)
    socket_path: str = "/ws/board"
    command_timeout_sec: float = Field(default=5.0, gt=0)
    watchdog_sec: float = Field(default=15.0, gt=0)
    claim_ttl_sec: int = Field(default=120, ge=10, le=3600)


class VoiceSettings(_Section):
    """Remote speech services the board microphone is streamed to.

    Attributes:
        enabled: Whether spoken commands are carried out at all.
        base_url: Address of the speech service.
        timeout_sec: How long a call to the speech service may take.
        sample_rate: Rate of the samples the board sends.
        max_audio_sec: Length of one recorded phrase.
        min_audio_bytes: Smallest clip worth sending to the recognizer.
        synthesis_enabled: Whether answers are spoken back.
        vad_threshold: Level above which the board counts the room as loud.
        neural_commands: Whether the remote understanding is used.
        bootstrap_url: Address of the remote understanding service.
    """

    model_config = SettingsConfigDict(env_prefix="VOICE_")

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
    """Natural language understanding pipeline.

    Attributes:
        model_name: Name of the sentence encoder.
        embedding_dimensions: Length of the vectors the encoder produces.
        device: Device the encoder runs on.
        confidence_threshold: How sure the pipeline has to be to act.
    """

    model_config = SettingsConfigDict(env_prefix="LANGUAGE_")

    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimensions: int = Field(default=384, ge=8, le=4096)
    device: str = "cpu"
    confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)


class TelegramSettings(_Section):
    """Telegram bot delivering notifications and accepting commands.

    Attributes:
        enabled: Whether the bot is started at all.
        bot_token: Token the bot talks to Telegram with.
        notify_chat_id: Chat the notifications are delivered to.
    """

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")

    enabled: bool = False
    bot_token: SecretStr = SecretStr("")
    notify_chat_id: str = ""

    @property
    def active(self) -> bool:
        """Return whether the bot may be started.

        Returns:
            bool: True when the bot is enabled and a token is configured.
        """
        return self.enabled and bool(self.bot_token.get_secret_value())


class AutomationTimings(_Section):
    """Periods of the background business cycles.

    Attributes:
        cycle_sec: How often the automation cycle runs.
        scenario_tick_sec: How often the scenarios are advanced.
        manual_override_minutes: How long a manual command holds automation back.
        summary_ttl_sec: Shortest interval between two progress messages.
    """

    model_config = SettingsConfigDict(env_prefix="AUTOMATION_")

    cycle_sec: float = Field(default=10.0, gt=0)
    scenario_tick_sec: float = Field(default=5.0, gt=0)
    manual_override_minutes: int = Field(default=30, ge=0, le=1440)
    summary_ttl_sec: int = Field(default=600, ge=30, le=86400)


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
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
        validate_default=True,
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
    automation: AutomationTimings = Field(default_factory=AutomationTimings)
