"""Метрики наблюдаемости сервиса поверх Prometheus-реестра.

Журнал отвечает на вопрос «что случилось», метрика — на вопрос «сколько раз и как
долго». Правило, зафиксированное в ТЗ: сбои, повторяющиеся каждый такт, должны попадать
в метрику, а не только в лог, иначе деградация тонула бы в потоке записей. Здесь собраны
счётчики команд железу и ошибок такта и гистограмма длительности цикла — ровно то, по
чему можно построить алерт, не читая логи.

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
BOARD_SESSIONS = Gauge(
    "smart_home_board_online",
    "Платы, чьё присутствие сейчас отмечено в реестре.",
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
