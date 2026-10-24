"""Фоновые циклы умного дома — вне HTTP-процесса.

Два цикла раньше жили фоновыми задачами внутри веб-сервера, что означало:
перезагрузка, масштабирование или вторая реплика молча умножали их. Теперь это
задачи ARQ-рабочего, читающего из Redis. Рабочих может быть несколько
одновременно, поэтому каждая задача по аккаунту сначала берёт распределённую
аренду с именем аккаунта: из двух инстансов, взявших один период, ровно один
его выполнит, а второй пропустит.

Аккаунты одного периода обрабатываются параллельно под семафором и каждый со
своим таймаутом, поэтому один дом с недоступной платой не задерживает
остальные; упавший аккаунт пишется в лог с трейсбеком, а прочие продолжают
работу. Периоды — секунды, а не календарные минуты, которые cron выразить не
может, поэтому два горячих цикла планируются задачами на старте и снимаются на
остановке, а часовая чистка устаревших объявлений плат — как раз для cron.
Каждая задача вызывается и сама по себе: именно это даёт возможность тестировать
цикл, не дожидаясь его.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Final

from arq import cron
from arq.connections import RedisSettings
from arq.worker import func
from dishka import AsyncContainer
from dishka.integrations.arq import DISHKA_APP_CONTAINER_KEY, setup_dishka

from backend.application.interfaces.queries.account_queries import AccountQueries
from backend.application.interfaces.services.messaging.notification_factory import (
    NotificationFactory,
)
from backend.application.interfaces.services.system.distributed_lock import DistributedLock
from backend.application.services.automation_service import AutomationService
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.application.services.scenarios.advancing import ScenarioAdvancer
from backend.config.settings import Settings
from backend.domain.identifiers import UserId
from backend.infrastructure.di import build_dishka_container
from backend.infrastructure.system.logging import configure_logging, get_logger

log = get_logger("worker")

WORKER_CONTEXT_KEY: Final = "worker_context"
AUTOMATION_LOCK: Final = "automation"
SCENARIO_LOCK: Final = "scenario"

UserJob = Callable[[UserId], Awaitable[object]]


@dataclass(frozen=True, slots=True)
class WorkerLimits:
    """Пределы, с которыми рабочий обслуживает аккаунты.

    Атрибуты перечислены вместо того, чтобы держать их константами модуля: это
    числа развёртывания, и приходят они из конфигурации.

    Attributes:
        max_concurrent_users: Сколько аккаунтов ведётся одновременно.
        per_user_timeout_sec: Сколько отводится на один аккаунт.
        lock_ttl_sec: Изначальное время жизни аренды.
        lock_refresh_sec: Как часто аренда продлевается.
    """

    max_concurrent_users: int
    per_user_timeout_sec: int
    lock_ttl_sec: int
    lock_refresh_sec: int

    @classmethod
    def of(cls, settings: Settings) -> WorkerLimits:
        """Собирает пределы из конфигурации процесса.

        Args:
            settings: Конфигурация, с которой работает рабочий.

        Returns:
            WorkerLimits: Пределы параллельности и аренд.
        """
        return cls(
            max_concurrent_users=settings.worker_max_concurrent_users,
            per_user_timeout_sec=settings.worker_per_user_timeout_sec,
            lock_ttl_sec=settings.worker_lock_ttl_sec,
            lock_refresh_sec=settings.worker_lock_refresh_sec,
        )


@dataclass(slots=True)
class WorkerContext:
    """Состояние рабочего процесса между его задачами.

    Attributes:
        settings: Конфигурация, с которой идут циклы.
        loops: Периодические циклы, запущенные на старте и снятые на остановке.
    """

    settings: Settings
    loops: list[asyncio.Task[None]] = field(default_factory=list)


def worker_settings(
    settings: Settings,
    notifications: NotificationFactory | None = None,
) -> type[Any]:
    """Собирает класс настроек, с которым запускается ARQ.

    Формулировки уведомлений приходят извне, а не выдумываются здесь: без них
    контейнер собирает молчаливые сообщения, и рабочий не сможет сказать человеку,
    что сценарий завершился.

    Args:
        settings: Конфигурация, с которой работает рабочий.
        notifications: Строит формулировки уведомлений этого процесса.

    Returns:
        type[Any]: Класс, из которого ARQ берёт аргументы рабочего.
    """
    built = _worker_class(settings)
    setup_dishka(build_dishka_container(settings, notifications=notifications), built)
    return built


def _worker_class(settings: Settings) -> type[Any]:
    """Строит класс настроек ARQ под это развёртывание."""

    class WorkerSettings:
        """Всё, что нужно ARQ для фоновых циклов системы."""

        functions: ClassVar[list[Any]] = [
            func(automation_cycle, timeout=settings.worker_job_timeout_sec),
            func(scenario_tick, timeout=settings.worker_job_timeout_sec),
            func(purge_board_claims, timeout=settings.worker_job_timeout_sec),
        ]
        cron_jobs: ClassVar[list[Any]] = [cron(purge_board_claims, minute={0}, second={0})]
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        queue_name = settings.worker_queue_name
        on_startup = staticmethod(startup)
        on_shutdown = staticmethod(shutdown)
        max_jobs = settings.worker_max_jobs
        job_timeout = settings.worker_job_timeout_sec
        keep_result = 0

    return WorkerSettings


async def startup(ctx: dict[str, Any]) -> None:
    """Готовит рабочий: логирование, типизированный контекст и периодические циклы.

    Конфигурация приходит из контейнера, который собрал композиционный корень,
    поэтому рабочий не читает окружение сам.

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
    """
    container = container_of(ctx)
    settings: Settings = await container.get(Settings)
    configure_logging(settings.app_log_level)
    context = WorkerContext(settings=settings)
    context.loops.extend(
        [
            asyncio.create_task(
                _every(ctx, automation_cycle, "automation", settings.automation_cycle_sec)
            ),
            asyncio.create_task(
                _every(ctx, scenario_tick, "scenarios", settings.automation_scenario_tick_sec)
            ),
        ]
    )
    ctx[WORKER_CONTEXT_KEY] = context
    log.info(
        "worker.started",
        queue=settings.worker_queue_name,
        automation_sec=settings.automation_cycle_sec,
        scenario_sec=settings.automation_scenario_tick_sec,
    )


async def shutdown(ctx: dict[str, Any]) -> None:
    """Снимает периодические циклы.

    Args:
        ctx: Контекст рабочего.
    """
    context = ctx.get(WORKER_CONTEXT_KEY)
    if isinstance(context, WorkerContext):
        for loop in context.loops:
            loop.cancel()
        for loop in context.loops:
            try:
                await loop
            except asyncio.CancelledError:
                continue
    log.info("worker.stopped")


async def automation_cycle(ctx: dict[str, Any]) -> None:
    """Прогоняет один цикл автоматизации для каждого зарегистрированного аккаунта.

    Аккаунты идут параллельно под общим семафором, каждый за своей арендой и со
    своим таймаутом: два инстанса рабочего по-прежнему выполняют по циклу на
    аккаунт, а один сломанный дом не останавливает остальные.

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
    """
    container = container_of(ctx)
    automation = await container.get(AutomationService)
    await _per_user(container, automation.run_cycle, AUTOMATION_LOCK)


async def scenario_tick(ctx: dict[str, Any]) -> None:
    """Двигает сценарии каждого зарегистрированного аккаунта.

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
    """
    container = container_of(ctx)
    advancer = await container.get(ScenarioAdvancer)
    await _per_user(container, advancer.advance, SCENARIO_LOCK)


async def _per_user(container: AsyncContainer, run: UserJob, lock_name: str) -> None:
    """Прогоняет одну работу по всем аккаунтам под их арендами.

    Args:
        container: Контейнер рабочего процесса.
        run: Работа, выполняемая для одного аккаунта.
        lock_name: Префикс ключа аренды.
    """
    settings: Settings = await container.get(Settings)
    lock = await container.get(DistributedLock)
    await run_for_each_user(
        await _user_ids(container),
        run,
        lock,
        lock_name=lock_name,
        limits=WorkerLimits.of(settings),
    )


async def purge_board_claims(ctx: dict[str, Any]) -> None:
    """Убирает объявления плат, которые никто не забрал.

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
    """
    onboarding = await container_of(ctx).get(BoardOnboardingService)
    removed = await onboarding.purge_expired_claims()
    if removed:
        log.info("worker.claims_purged", removed=removed)


async def run_for_each_user(
    user_ids: Sequence[UserId],
    run: UserJob,
    lock: DistributedLock,
    *,
    lock_name: str,
    limits: WorkerLimits,
) -> None:
    """Выполняет по единице работы на аккаунт: параллельно и не больше одного раза.

    Каждый аккаунт берёт слот общего семафора, аренду по ключу
    ``{lock_name}:<user_id>`` и собственный таймаут. Занятая аренда означает, что
    аккаунт сейчас обслуживает другой рабочий; ошибка или таймаут пишутся в лог с
    трейсбеком и не мешают остальным аккаунтам.

    Args:
        user_ids: Аккаунты этого периода.
        run: Работа для одного аккаунта.
        lock: Распределённая аренда, не дающая двум рабочим взять один аккаунт.
        lock_name: Префикс ключа аренды.
        limits: Пределы параллельности и аренд.
    """
    semaphore = asyncio.Semaphore(limits.max_concurrent_users)
    async with asyncio.TaskGroup() as group:
        for user_id in user_ids:
            group.create_task(_run_user(user_id, run, lock, lock_name, semaphore, limits))


async def _run_user(
    user_id: UserId,
    run: UserJob,
    lock: DistributedLock,
    lock_name: str,
    semaphore: asyncio.Semaphore,
    limits: WorkerLimits,
) -> None:
    """Выполняет работу одного аккаунта под его арендой и слотом семафора.

    Args:
        user_id: Обслуживаемый аккаунт.
        run: Работа для аккаунта.
        lock: Распределённая аренда аккаунта.
        lock_name: Префикс ключа аренды.
        semaphore: Общий предел одновременно ведемых аккаунтов.
        limits: Пределы параллельности и аренд.
    """
    async with semaphore:
        try:
            async with lock.acquire(
                f"{lock_name}:{user_id}",
                ttl_sec=limits.lock_ttl_sec,
                refresh_sec=limits.lock_refresh_sec,
            ):
                await _run_guarded(user_id, run, limits.per_user_timeout_sec)
        except TimeoutError:
            log.info("worker.user_skipped", user=str(user_id), lock=lock_name)


async def _run_guarded(user_id: UserId, run: UserJob, timeout_sec: int) -> None:
    """Выполняет работу аккаунта с её таймаутом и полным трейсбеком.

    Args:
        user_id: Обслуживаемый аккаунт.
        run: Работа для аккаунта.
        timeout_sec: Секунды, отведённые на работу.
    """
    try:
        async with asyncio.timeout(timeout_sec):
            await run(user_id)
    except TimeoutError:
        log.warning("worker.user_timed_out", user=str(user_id), timeout_sec=timeout_sec)
    except Exception:
        log.exception("worker.user_failed", user=str(user_id))


def run_worker(
    settings: Settings,
    notifications: NotificationFactory | None = None,
) -> None:
    """Запускает рабочий до его остановки.

    ARQ сам ведёт цикл событий, поэтому функция обычная, а не корутина: иначе
    вызывающий получил бы обещание вместо запущенного процесса.

    Args:
        settings: Конфигурация, с которой работает рабочий.
        notifications: Строит формулировки уведомлений этого процесса.
    """
    from arq.worker import run_worker as run

    run(worker_settings(settings, notifications))


def container_of(ctx: dict[str, Any]) -> AsyncContainer:
    """Возвращает контейнер рабочего процесса.

    Args:
        ctx: Контекст рабочего.

    Returns:
        AsyncContainer: Контейнер, которым рабочие задачи разрешаются.
    """
    container: AsyncContainer = ctx[DISHKA_APP_CONTAINER_KEY]
    return container


async def _user_ids(container: AsyncContainer) -> list[UserId]:
    """Возвращает аккаунты, которых должен обслужить период.

    Args:
        container: Контейнер рабочего процесса.

    Returns:
        list[UserId]: Идентификаторы всех зарегистрированных аккаунтов.
    """
    queries: AccountQueries = await container.get(AccountQueries)
    return await queries.list_registered_ids()


async def _every(
    ctx: dict[str, Any],
    job: Callable[[dict[str, Any]], Awaitable[None]],
    name: str,
    period_sec: float,
) -> None:
    """Повторяет задачу каждые `period_sec` секунд, пока рабочий не остановлен.

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
        job: Повторяемый цикл.
        name: Какой это цикл — для записи об ошибке.
        period_sec: Секунды между запусками.
    """
    while True:
        await asyncio.sleep(period_sec)
        try:
            await job(ctx)
        except Exception:
            log.exception("worker.loop_failed", loop=name)
