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
может, поэтому у планирования ровно один механизм: два горячих цикла живут
задачами процесса на старте и снимаются на остановке, каждый со своим таймаутом
из конфигурации, а чистка устаревших объявлений плат ходит раз в минуту: окно
объявления живёт две минуты, и реже было бы копить строки, которые никто не
заберёт. Для такого расписания ARQ-cron и предназначен. Задачи не дублируются в
объявлении ARQ: цикл, который никто не ставит в очередь, там только вводил бы в
заблуждение.
Цикл вызывается и сам по себе: именно это даёт возможность тестировать его,
не дожидаясь расписания.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Final

from arq import cron
from arq.connections import RedisSettings
from arq.worker import func
from dishka import AsyncContainer
from dishka.integrations.arq import DISHKA_APP_CONTAINER_KEY, setup_dishka

from backend.application.interfaces.queries.account_queries import AccountQueries
from backend.application.interfaces.services.system.distributed_lock import (
    DistributedLock,
    LeaseLostError,
    LockBusyError,
    LockUnavailableError,
)
from backend.application.services.automation_service import AutomationService
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.application.services.scenarios.advancing import ScenarioAdvancer
from backend.config.settings import Settings
from backend.domain.identifiers import UserId
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from backend.infrastructure.system import metrics
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


def worker_settings(settings: Settings, container: AsyncContainer) -> type[Any]:
    """Собирает класс настроек, с которым запускается ARQ.

    Граф приходит готовым: его собрала композиция с той ролью и теми
    формулировками, которые нужны этому процессу. Здесь остаётся только связать его
    с задачами ARQ, чтобы каждая из них разрешала свои зависимости из него.

    Args:
        settings: Конфигурация, с которой работает рабочий.
        container: Граф зависимостей роли рабочего.

    Returns:
        type[Any]: Класс, из которого ARQ берёт аргументы рабочего.
    """
    built = _worker_class(settings)
    setup_dishka(container, built)
    return built


def _worker_class(settings: Settings) -> type[Any]:
    """Строит класс настроек ARQ под это развёртывание.

    В объявлении остаётся только то, что ARQ действительно исполняет: чистка
    объявлений плат по расписанию. Горячие циклы в очередь никто не ставит, и
    объявление их задачами ARQ было бы мёртвой конфигурацией: таймаут из неё ни
    на что не влиял бы.
    """

    class WorkerSettings:
        """Всё, что нужно ARQ для фоновых циклов системы."""

        functions: ClassVar[list[Any]] = [
            func(purge_board_claims, timeout=settings.worker_job_timeout_sec),
        ]
        cron_jobs: ClassVar[list[Any]] = [cron(purge_board_claims, second={0})]
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
                _every(
                    ctx,
                    automation_cycle,
                    AUTOMATION_LOCK,
                    settings.automation_cycle_sec,
                    settings.worker_loop_timeout_sec,
                )
            ),
            asyncio.create_task(
                _every(
                    ctx,
                    scenario_tick,
                    SCENARIO_LOCK,
                    settings.automation_scenario_tick_sec,
                    settings.worker_loop_timeout_sec,
                )
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
    """Прогоняет один цикл автоматизации для каждого аккаунта с подключённой платой.

    Аккаунты берутся из реестра присутствия Redis, а не полным сканированием базы: без
    онлайн-платы автоматизировать нечего, а такт не растёт от числа зарегистрированных.

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
    """
    container = container_of(ctx)
    automation = await container.get(AutomationService)
    presence = await container.get(RedisBoardPresence)
    online = await presence.online_user_ids()
    await _per_user(container, automation.run_cycle, AUTOMATION_LOCK, online)


async def scenario_tick(ctx: dict[str, Any]) -> None:
    """Двигает сценарии каждого зарегистрированного аккаунта.

    Здесь список остаётся полным: ожидающий или идущий сценарий надо двигать и когда
    плата недоступна (иначе он зависнет, а не перейдёт в отказ).

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
    """
    container = container_of(ctx)
    advancer = await container.get(ScenarioAdvancer)
    await _per_user(container, advancer.advance, SCENARIO_LOCK, await _user_ids(container))


async def _per_user(
    container: AsyncContainer,
    run: UserJob,
    lock_name: str,
    user_ids: Sequence[UserId],
) -> None:
    """Прогоняет одну работу по переданным аккаунтам под их арендами.

    Args:
        container: Контейнер рабочего процесса.
        run: Работа, выполняемая для одного аккаунта.
        lock_name: Префикс ключа аренды.
        user_ids: Аккаунты этого периода.
    """
    settings: Settings = await container.get(Settings)
    lock = await container.get(DistributedLock)
    started = time.perf_counter()
    await run_for_each_user(
        user_ids,
        run,
        lock,
        lock_name=lock_name,
        limits=WorkerLimits.of(settings),
    )
    metrics.observe_cycle(lock_name, time.perf_counter() - started)


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

    Три отказа аренды приходят сюда разными типами, потому что и значат они разное.
    Занятая аренда — обычное дело: аккаунт уже обслуживает сосед, и этот круг ему
    не нужен. Молчащий Redis — деградация, о которой надо сказать громче. Потеря
    аренды посреди работы — инцидент: тот же дом мог уже взять кто-то другой, и
    продолжение дублировало бы команды.

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
                await _run_guarded(user_id, run, limits.per_user_timeout_sec, lock_name)
        except LockBusyError:
            log.info("worker.user_skipped", user=str(user_id), lock=lock_name)
        except LockUnavailableError:
            metrics.count_cycle_error(lock_name)
            log.warning("worker.lock_unavailable", user=str(user_id), lock=lock_name)
        except LeaseLostError:
            metrics.count_cycle_error(lock_name)
            log.error("worker.lease_lost", user=str(user_id), lock=lock_name)


async def _run_guarded(user_id: UserId, run: UserJob, timeout_sec: int, cycle: str) -> None:
    """Выполняет работу аккаунта с её таймаутом и полным трейсбеком.

    Ошибка и таймаут считаются разными счётчиками: ошибка означает, что цикл упал,
    а таймаут — что он не успел, и лечатся они по-разному.

    Args:
        user_id: Обслуживаемый аккаунт.
        run: Работа для аккаунта.
        timeout_sec: Секунды, отведённые на работу.
        cycle: Название цикла — метка метрики: всплеск не тонет в журнале.
    """
    try:
        async with asyncio.timeout(timeout_sec):
            await run(user_id)
    except TimeoutError:
        metrics.count_cycle_timeout(cycle)
        log.warning(
            "worker.user_timed_out",
            user=str(user_id),
            cycle=cycle,
            timeout_sec=timeout_sec,
        )
    except Exception:
        metrics.count_cycle_error(cycle)
        log.exception("worker.user_failed", user=str(user_id))


def run_worker(settings: Settings, container: AsyncContainer) -> None:
    """Запускает рабочий до его остановки.

    ARQ сам ведёт цикл событий, поэтому функция обычная, а не корутина: иначе
    вызывающий получил бы обещание вместо запущенного процесса.

    Args:
        settings: Конфигурация, с которой работает рабочий.
        container: Граф зависимостей роли рабочего.
    """
    from arq.worker import run_worker as run

    run(worker_settings(settings, container))


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
    timeout_sec: int,
) -> None:
    """Повторяет задачу каждые `period_sec` секунд, пока рабочий не остановлен.

    Такт ограничен собственным таймаутом: зависший обход домов не должен сдвигать
    следующий. Отказ такта остаётся виден дважды — в журнале с трейсбеком и в
    метрике с именем цикла, — иначе редкая деградация тонула бы в потоке записей.

    Args:
        ctx: Контекст рабочего, уже несущий контейнер.
        job: Повторяемый цикл.
        name: Имя цикла — метка метрики и записи об ошибке.
        period_sec: Секунды между запусками.
        timeout_sec: Сколько может длиться один такт.
    """
    while True:
        await asyncio.sleep(period_sec)
        try:
            async with asyncio.timeout(timeout_sec):
                await job(ctx)
        except TimeoutError:
            metrics.count_cycle_timeout(name)
            log.warning("worker.loop_timed_out", loop=name, timeout_sec=timeout_sec)
        except Exception:
            metrics.count_cycle_error(name)
            log.exception("worker.loop_failed", loop=name)
