"""Background cycles of the smart home, outside the HTTP process.

Two cycles used to run as background tasks inside the web server, which meant a
reload, a scale out or a second replica silently multiplied them. They live here
instead, as jobs of an ARQ worker reading from Redis: several workers may run
this at the same time, and the throttle of the state store keeps two of them from
doing the same work twice.

The periods are seconds rather than calendar minutes, which a cron expression
cannot express, so the two hot loops are scheduled as tasks on startup and
cancelled on shutdown. The cleanup of stale board announcements uses a cron
schedule, because an hourly job is exactly what that is. Every job stays callable
on its own, which is what makes a cycle testable without waiting for it.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Final

from arq import cron
from arq.connections import RedisSettings
from arq.worker import func
from dishka import AsyncContainer
from dishka.integrations.arq import DISHKA_APP_CONTAINER_KEY, setup_dishka

from smart_home.application.ports.queries.accounts import AccountQueries
from smart_home.application.services.automation_service import AutomationService
from smart_home.application.services.board_onboarding import BoardOnboardingService
from smart_home.application.services.scenario_service import ScenarioService
from smart_home.config.settings import Settings
from smart_home.infrastructure.di.container import make_container
from smart_home.infrastructure.logging import configure_logging, get_logger

log = get_logger("worker")

QUEUE_NAME: Final = "smart-home"
JOB_TIMEOUT_SECONDS: Final = 60
MAX_JOBS: Final = 4
SETTINGS_CONTEXT_KEY: Final = "settings"
LOOPS_CONTEXT_KEY: Final = "cycle_loops"

Cycle = Any


def worker_settings(settings: Settings) -> type[Any]:
    """Build the settings class ARQ is started with.

    Args:
        settings: Configuration the worker runs with.

    Returns:
        type[Any]: Class ARQ reads its worker arguments from.
    """
    built = _worker_class(settings)
    setup_dishka(make_container(settings), built)
    return built


def _worker_class(settings: Settings) -> type[Any]:
    class WorkerSettings:
        """Everything ARQ needs to run the background cycles of this system."""

        functions: ClassVar[list[Any]] = [
            func(automation_cycle, timeout=JOB_TIMEOUT_SECONDS),
            func(scenario_tick, timeout=JOB_TIMEOUT_SECONDS),
            func(purge_board_claims, timeout=JOB_TIMEOUT_SECONDS),
        ]
        cron_jobs: ClassVar[list[Any]] = [cron(purge_board_claims, minute={0}, second={0})]
        redis_settings = RedisSettings.from_dsn(settings.redis.url)
        queue_name = QUEUE_NAME
        on_startup = staticmethod(startup)
        on_shutdown = staticmethod(shutdown)
        max_jobs = MAX_JOBS
        job_timeout = JOB_TIMEOUT_SECONDS
        keep_result = 0

    return WorkerSettings


async def startup(ctx: dict[Any, Any]) -> None:
    """Start the periodic loops and remember them for shutdown.

    Args:
        ctx: Worker context, already carrying the container.

    Returns:
        None.
    """
    settings = settings_of(ctx)
    configure_logging(settings.server.log_level)
    ctx[SETTINGS_CONTEXT_KEY] = settings
    ctx[LOOPS_CONTEXT_KEY] = [
        asyncio.create_task(_every(ctx, "automation", settings.automation.cycle_sec)),
        asyncio.create_task(_every(ctx, "scenarios", settings.automation.scenario_tick_sec)),
    ]
    log.info(
        "worker.started",
        queue=QUEUE_NAME,
        automation_sec=settings.automation.cycle_sec,
        scenario_sec=settings.automation.scenario_tick_sec,
    )


async def shutdown(ctx: dict[Any, Any]) -> None:
    """Cancel the periodic loops.

    Args:
        ctx: Worker context.

    Returns:
        None.
    """
    loops: list[asyncio.Task[None]] = ctx.get(LOOPS_CONTEXT_KEY, [])
    for loop in loops:
        loop.cancel()
    for loop in loops:
        try:
            await loop
        except asyncio.CancelledError:
            continue
    log.info("worker.stopped")


async def automation_cycle(ctx: dict[Any, Any]) -> None:
    """Run one automation cycle for every registered account.

    One account that fails never stops the others: a cycle is per home and a
    broken home is not a broken deployment.

    Args:
        ctx: Worker context, already carrying the container.

    Returns:
        None.
    """
    container = container_of(ctx)
    automation = await container.get(AutomationService)
    for user_id in await _user_ids(container):
        try:
            await automation.run_cycle(user_id)
        except Exception as error:
            log.error("worker.automation_failed", user=str(user_id), error=str(error))


async def scenario_tick(ctx: dict[Any, Any]) -> None:
    """Advance the scenarios of every registered account.

    Args:
        ctx: Worker context, already carrying the container.

    Returns:
        None.
    """
    container = container_of(ctx)
    scenarios = await container.get(ScenarioService)
    for user_id in await _user_ids(container):
        try:
            await scenarios.advance(user_id)
        except Exception as error:
            log.error("worker.scenario_failed", user=str(user_id), error=str(error))


async def purge_board_claims(ctx: dict[Any, Any]) -> None:
    """Remove the board announcements nobody took.

    Args:
        ctx: Worker context, already carrying the container.

    Returns:
        None.
    """
    removed = await (await container_of(ctx).get(BoardOnboardingService)).purge_expired_claims()
    if removed:
        log.info("worker.claims_purged", removed=removed)


async def run_worker(settings: Settings) -> None:
    """Run the worker until it is stopped.

    Args:
        settings: Configuration the worker runs with.

    Returns:
        None.
    """
    from arq.worker import run_worker as run

    run(worker_settings(settings))


def container_of(ctx: dict[Any, Any]) -> AsyncContainer:
    """Return the container of the worker process.

    Args:
        ctx: Worker context.

    Returns:
        AsyncContainer: Container ARQ resolves the jobs with.
    """
    container: AsyncContainer = ctx[DISHKA_APP_CONTAINER_KEY]
    return container


def settings_of(ctx: dict[Any, Any]) -> Settings:
    """Return the configuration the worker runs with.

    Args:
        ctx: Worker context.

    Returns:
        Settings: Configuration remembered at startup.

    Raises:
        RuntimeError: When the context does not carry the configuration, which
            means the worker was started without the composition root.
    """
    stored = ctx.get(SETTINGS_CONTEXT_KEY)
    if not isinstance(stored, Settings):
        raise RuntimeError("the worker context does not carry the configuration")
    return stored


async def _user_ids(container: AsyncContainer) -> list[Any]:
    return await (await container.get(AccountQueries)).list_registered_ids()


async def _every(ctx: dict[Any, Any], name: str, period_sec: float) -> None:
    while True:
        await asyncio.sleep(period_sec)
        try:
            if name == "automation":
                await automation_cycle(ctx)
            else:
                await scenario_tick(ctx)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.error("worker.loop_failed", loop=name, error=str(error))
