"""Фоновый рабочий: очередь, сроки и одновременно обслуживаемые аккаунты."""

from __future__ import annotations

import os


def worker_queue_name() -> str:
    """Имя очереди задач фонового рабочего.

    Returns:
        str: Имя очереди.
    """
    return os.getenv("WORKER_QUEUE_NAME", "smart-home")


def worker_job_timeout_sec() -> int:
    """Сколько может длиться одна задача рабочего.

    Returns:
        int: Секунды ожидания.
    """
    return int(os.getenv("WORKER_JOB_TIMEOUT_SEC", "60"))


def worker_max_jobs() -> int:
    """Сколько задач рабочий держит одновременно.

    Returns:
        int: Предел параллельных задач.
    """
    return int(os.getenv("WORKER_MAX_JOBS", "4"))


def worker_max_concurrent_users() -> int:
    """Сколько аккаунтов обслуживается параллельно.

    Returns:
        int: Предел одновременных аккаунтов.
    """
    return int(os.getenv("WORKER_MAX_CONCURRENT_USERS", "4"))


def worker_per_user_timeout_sec() -> int:
    """Сколько отводится на работу с одним аккаунтом.

    Returns:
        int: Секунды ожидания.
    """
    return int(os.getenv("WORKER_PER_USER_TIMEOUT_SEC", "20"))


def worker_lock_ttl_sec() -> int:
    """Изначальное время жизни аренды аккаунта.

    Returns:
        int: Секунды аренды.
    """
    return int(os.getenv("WORKER_LOCK_TTL_SEC", "30"))


def worker_lock_refresh_sec() -> int:
    """Как часто аренда аккаунта продлевается.

    Returns:
        int: Секунды между продлениями.
    """
    return int(os.getenv("WORKER_LOCK_REFRESH_SEC", "10"))
