"""Настройки приложения, собранные из переменных окружения.

Значения читаются в момент вычисления тела класса вызовом чистых функций из
`backend.config.sections`, поэтому повторный импорт модуля пересобирает их из
текущего окружения. Класс плоский: имя настройки повторяет имя переменной
окружения, а не превращается в предложение из слов.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from backend.config.sections import (
    auth,
    automation,
    board,
    database,
    devices,
    http,
    language,
    redis_,
    security,
    server,
    telegram,
    worker,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Настройки приложения, прочитанные из переменных окружения."""

    app_name: str = server.app_name()
    app_host: str = server.app_host()
    app_port: int = server.app_port()
    app_log_level: str = server.app_log_level()
    app_cors_allowed_origins: list[str] = server.app_cors_allowed_origins()

    auth_token_secret: str = auth.auth_token_secret()
    auth_session_lifetime_minutes: int = auth.auth_session_lifetime_minutes()

    database_url: str = database.database_url()
    database_echo: bool = database.database_echo()
    database_pool_size: int = database.database_pool_size()
    database_pool_max_overflow: int = database.database_pool_max_overflow()
    database_pool_recycle_sec: int = database.database_pool_recycle_sec()

    redis_url: str = redis_.redis_url()
    redis_password: str | None = redis_.redis_password()
    redis_key_prefix: str = redis_.redis_key_prefix()

    board_socket_port: int = board.board_socket_port()
    board_socket_path: str = board.board_socket_path()
    board_command_timeout_sec: float = board.board_command_timeout_sec()
    board_watchdog_sec: float = board.board_watchdog_sec()
    board_claim_ttl_sec: int = board.board_claim_ttl_sec()
    board_handshake_timeout_sec: float = board.board_handshake_timeout_sec()
    board_ping_interval_sec: int = board.board_ping_interval_sec()
    board_ping_timeout_sec: int = board.board_ping_timeout_sec()

    language_model_name: str = language.language_model_name()
    language_embedding_dimensions: int = language.language_embedding_dimensions()
    language_device: str = language.language_device()
    language_confidence_threshold: float = language.language_confidence_threshold()
    language_neural_commands: bool = language.language_neural_commands()
    language_bootstrap_url: str = language.language_bootstrap_url()
    language_timeout_sec: float = language.language_timeout_sec()

    telegram_enabled: bool = telegram.telegram_enabled()
    telegram_bot_token: str = telegram.telegram_bot_token()
    telegram_notify_chat_id: str = telegram.telegram_notify_chat_id()
    telegram_link_lifetime_min: int = telegram.telegram_link_lifetime_min()

    automation_cycle_sec: float = automation.automation_cycle_sec()
    automation_scenario_tick_sec: float = automation.automation_scenario_tick_sec()
    automation_manual_override_minutes: int = automation.automation_manual_override_minutes()
    automation_summary_ttl_sec: int = automation.automation_summary_ttl_sec()
    automation_scenario_summary_ttl_sec: int = automation.automation_scenario_summary_ttl_sec()

    pbkdf2_iterations: int = security.pbkdf2_iterations()
    password_salt_bytes: int = security.password_salt_bytes()
    token_leeway_seconds: int = security.token_leeway_seconds()

    http_max_connections: int = http.http_max_connections()
    http_max_keepalive_connections: int = http.http_max_keepalive_connections()

    device_refresh_attempts: int = devices.device_refresh_attempts()

    worker_queue_name: str = worker.worker_queue_name()
    worker_job_timeout_sec: int = worker.worker_job_timeout_sec()
    worker_max_jobs: int = worker.worker_max_jobs()
    worker_max_concurrent_users: int = worker.worker_max_concurrent_users()
    worker_per_user_timeout_sec: int = worker.worker_per_user_timeout_sec()
    worker_lock_ttl_sec: int = worker.worker_lock_ttl_sec()
    worker_lock_refresh_sec: int = worker.worker_lock_refresh_sec()

    @property
    def telegram_active(self) -> bool:
        """Может ли бот быть запущен.

        Returns:
            bool: True, когда бот включён и токен задан.
        """
        return self.telegram_enabled and bool(self.telegram_bot_token)
