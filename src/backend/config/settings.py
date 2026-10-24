"""Настройки приложения, собранные из переменных окружения.

Значения читаются не при импорте модуля, а в момент создания `Settings()`: импорт
любого сервиса, который просто ссылается на тип `Settings`, больше не требует валидного
`.env` и не падает сам по себе. Ошибка конфигурации приходит рано и ровно там, где
настройки начинают использовать, — в композиционном корне процесса.

Класс плоский: имя настройки повторяет имя переменной окружения, а не превращается в
предложение из слов. Список разрешённых CORS-источников — неизменяемый `tuple`, чтобы
ни один потребитель не мутировал общий список. `.env` ищётся через `find_dotenv` от
текущей рабочей директории, а не по фиксированной глубине файла, поэтому перенос модуля
или нестандартная сборка путь не ломают.
"""

from __future__ import annotations

from dotenv import find_dotenv, load_dotenv

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


class Settings:
    """Настройки приложения, прочитанные из переменных окружения при создании."""

    def __init__(self) -> None:
        """Читает `.env` и собирает все значения из окружения.

        Порядок один: `.env` поднимается к текущей рабочей директории, затем каждое поле
        берётся из своей функции-загрузчика секции, поэтому вся конфигурация складывается
        в одном месте, а не по всему коду.
        """
        load_dotenv(find_dotenv(usecwd=True))

        self.app_name: str = server.app_name()
        self.app_host: str = server.app_host()
        self.app_port: int = server.app_port()
        self.app_log_level: str = server.app_log_level()
        self.app_cors_allowed_origins: tuple[str, ...] = tuple(
            server.app_cors_allowed_origins()
        )

        self.auth_token_secret: str = auth.auth_token_secret()
        self.auth_session_lifetime_minutes: int = auth.auth_session_lifetime_minutes()
        self.realtime_ticket_ttl_sec: int = auth.realtime_ticket_ttl_sec()

        self.database_url: str = database.database_url()
        self.database_echo: bool = database.database_echo()
        self.database_pool_size: int = database.database_pool_size()
        self.database_pool_max_overflow: int = database.database_pool_max_overflow()
        self.database_pool_recycle_sec: int = database.database_pool_recycle_sec()

        self.redis_url: str = redis_.redis_url()
        self.redis_password: str | None = redis_.redis_password()
        self.redis_key_prefix: str = redis_.redis_key_prefix()

        self.board_socket_port: int = board.board_socket_port()
        self.board_socket_path: str = board.board_socket_path()
        self.board_command_timeout_sec: float = board.board_command_timeout_sec()
        self.board_watchdog_sec: float = board.board_watchdog_sec()
        self.board_presence_ttl_sec: float = board.board_presence_ttl_sec()
        self.board_command_result_timeout_sec: float = board.board_command_result_timeout_sec()
        self.board_claim_ttl_sec: int = board.board_claim_ttl_sec()
        self.board_handshake_timeout_sec: float = board.board_handshake_timeout_sec()
        self.board_ping_interval_sec: int = board.board_ping_interval_sec()
        self.board_ping_timeout_sec: int = board.board_ping_timeout_sec()

        self.language_model_name: str = language.language_model_name()
        self.language_embedding_dimensions: int = language.language_embedding_dimensions()
        self.language_device: str = language.language_device()
        self.language_confidence_threshold: float = language.language_confidence_threshold()
        self.language_neural_commands: bool = language.language_neural_commands()
        self.language_bootstrap_url: str = language.language_bootstrap_url()
        self.language_timeout_sec: float = language.language_timeout_sec()

        self.telegram_enabled: bool = telegram.telegram_enabled()
        self.telegram_bot_token: str = telegram.telegram_bot_token()
        self.telegram_notify_chat_id: str = telegram.telegram_notify_chat_id()
        self.telegram_link_lifetime_min: int = telegram.telegram_link_lifetime_min()

        self.automation_cycle_sec: float = automation.automation_cycle_sec()
        self.automation_scenario_tick_sec: float = automation.automation_scenario_tick_sec()
        self.automation_manual_override_minutes: int = (
            automation.automation_manual_override_minutes()
        )
        self.automation_summary_ttl_sec: int = automation.automation_summary_ttl_sec()
        self.automation_scenario_summary_ttl_sec: int = (
            automation.automation_scenario_summary_ttl_sec()
        )

        self.pbkdf2_iterations: int = security.pbkdf2_iterations()
        self.password_salt_bytes: int = security.password_salt_bytes()
        self.token_leeway_seconds: int = security.token_leeway_seconds()

        self.http_max_connections: int = http.http_max_connections()
        self.http_max_keepalive_connections: int = http.http_max_keepalive_connections()

        self.device_refresh_attempts: int = devices.device_refresh_attempts()

        self.worker_queue_name: str = worker.worker_queue_name()
        self.worker_job_timeout_sec: int = worker.worker_job_timeout_sec()
        self.worker_max_jobs: int = worker.worker_max_jobs()
        self.worker_max_concurrent_users: int = worker.worker_max_concurrent_users()
        self.worker_per_user_timeout_sec: int = worker.worker_per_user_timeout_sec()
        self.worker_lock_ttl_sec: int = worker.worker_lock_ttl_sec()
        self.worker_lock_refresh_sec: int = worker.worker_lock_refresh_sec()

    @property
    def telegram_active(self) -> bool:
        """Может ли бот быть запущен.

        Returns:
            bool: True, когда бот включён и токен задан.
        """
        return self.telegram_enabled and bool(self.telegram_bot_token)
