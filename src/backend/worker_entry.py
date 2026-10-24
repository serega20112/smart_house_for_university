"""Точка входа рабочего процесса фоновых циклов.

Пар с ``backend.main``: конфигурация читается здесь, а контейнер собирается с теми
формулировками уведомлений, которые принадлежат презентационному слою. Без них рабочий
отдавал бы молчаливые сообщения, и человек не узнал бы ни о старте сценария, ни о его
конце.
"""

from __future__ import annotations

from backend.config import Settings
from backend.infrastructure.workers.worker import run_worker
from backend.presentation.messages import NotificationFactoryImpl


def main() -> None:
    """Запускает рабочий процесс с конфигурацией из окружения."""
    run_worker(Settings(), notifications=NotificationFactoryImpl())


if __name__ == "__main__":
    main()
