"""Метрики наблюдаемости сервиса поверх Prometheus-реестра.

Журнал отвечает на вопрос «что случилось», метрика — на вопрос «сколько раз и как
долго». Правило, зафиксированное в ТЗ: сбои, повторяющиеся каждый такт, должны попадать
в метрику, а не только в лог, иначе деградация тонула бы в потоке записей. Здесь собраны
счётчики команд железу, ошибок и таймаутов такта, обрывов чтения событий и гистограмма
длительности цикла — ровно то, по чему можно построить алерт, не читая логи.

Коллекторы регистрируются в общем реестре один раз при импорте; каждый процесс (API и
рабочий) поднимает свой экспортер `/metrics`, поэтому метрики не смешиваются между
развёртываниями.
"""

from __future__ import annotations

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

BOARD_COMMANDS = Counter(
    "smart_home_board_commands_total",
    "Команды, отправленные платам, по исходу.",
    ("outcome",),
)
BOARD_COMMAND_SECONDS = Histogram(
    "smart_home_board_command_seconds",
    "Длительность исполнения одной команды плате.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
CYCLE_SECONDS = Histogram(
    "smart_home_cycle_seconds",
    "Длительность одного такта рабочего цикла, по имени цикла.",
    ("cycle",),
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)
CYCLE_ERRORS = Counter(
    "smart_home_cycle_errors_total",
    "Ошибки аккаунтов внутри тактов рабочего, по имени цикла.",
    ("cycle",),
)
CYCLE_TIMEOUTS = Counter(
    "smart_home_cycle_timeouts_total",
    "Такты, не уложившиеся в отведённое время, по имени цикла.",
    ("cycle",),
)
BOARD_SESSIONS = Gauge(
    "smart_home_board_online",
    "Платы, чьё присутствие сейчас отмечено в реестре.",
)
STREAM_FAILURES = Counter(
    "smart_home_event_stream_failures_total",
    "Обрывы чтения потока событий, по имени потока.",
    ("stream",),
)


def record_board_command(outcome: str, seconds: float) -> None:
    """Записывает исход и длительность одной команды плате.

    Args:
        outcome: Итог команды — принята, отвергнута или не дошла.
        seconds: Сколько секунд заняло исполнение.
    """
    BOARD_COMMANDS.labels(outcome).inc()
    BOARD_COMMAND_SECONDS.observe(seconds)


def observe_cycle(cycle: str, seconds: float) -> None:
    """Записывает длительность одного такта рабочего цикла.

    Args:
        cycle: Название цикла (автоматика или сценарии).
        seconds: Сколько секунд занял такт.
    """
    CYCLE_SECONDS.labels(cycle).observe(seconds)


def count_cycle_error(cycle: str) -> None:
    """Записывает ошибку аккаунта внутри такта рабочего цикла.

    Args:
        cycle: Название цикла, в котором случилась ошибка.
    """
    CYCLE_ERRORS.labels(cycle).inc()


def count_cycle_timeout(cycle: str) -> None:
    """Записывает такт, не уложившийся в свой таймаут.

    Зависание лечится не так, как ошибка: плата не ответила или сеть легла. Общий
    счётчик ошибок показал бы «что-то сломалось», а этот — «дом не отвечает».

    Args:
        cycle: Название цикла, который не успел.
    """
    CYCLE_TIMEOUTS.labels(cycle).inc()


def count_stream_failure(stream: str) -> None:
    """Записывает обрыв чтения потока событий.

    Поток, который молча перестал читать, снаружи выглядит как тишина в доме,
    поэтому каждый обрыв должен быть виден на графике, а не только в журнале.

    Args:
        stream: Название потока — события интерфейса или команды платам.
    """
    STREAM_FAILURES.labels(stream).inc()


def set_board_sessions(count: int) -> None:
    """Выставляет текущее число подключённых плат.

    Args:
        count: Сколько плат отмечено присутствующими.
    """
    BOARD_SESSIONS.set(count)


def render() -> bytes:
    """Возвращает снимок всех метрик в текстовом формате Prometheus.

    Returns:
        bytes: Экспорт реестра для эндпоинта `/metrics`.
    """
    return generate_latest(REGISTRY)
