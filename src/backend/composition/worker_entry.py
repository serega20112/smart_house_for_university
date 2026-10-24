"""Точка входа фонового процесса: граф роли рабочего и запуск ARQ.

Пара к ``backend.composition.main``: там приложение слушает порт, здесь тот же граф
крутит периодические циклы. Обе точки выбирают конфигурацию и граф сами, поэтому ни
один слой ниже не решает, в каком процессе он оказался.
"""

from __future__ import annotations

from backend.composition.worker import build_worker_container
from backend.config import Settings
from backend.infrastructure.workers.worker import run_worker


def main() -> None:
    """Запускает рабочий процесс с конфигурацией из окружения."""
    settings = Settings()
    run_worker(settings, build_worker_container(settings))


if __name__ == "__main__":
    main()
