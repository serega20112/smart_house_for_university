"""Background loops of automation and scenarios.

Drives two periodic tasks, one per business cycle. The scheduler only knows the
use cases it has to call, so it stays independent of FastAPI and of any
infrastructure detail.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress

from smart_home_backend.application.use_cases.automation import RunAutomationCycleUseCase
from smart_home_backend.application.use_cases.scenario import TickScenariosUseCase

log = logging.getLogger("smart_home_backend.scheduler")


class BackgroundScheduler:
    """Starts and stops the periodic business cycles."""

    def __init__(
        self,
        run_automation: RunAutomationCycleUseCase,
        tick_scenarios: TickScenariosUseCase,
        automation_interval: float,
        scenario_interval: float,
    ) -> None:
        """Initialize the scheduler.

        Args:
            run_automation: Use case running one automation cycle.
            tick_scenarios: Use case advancing the scenarios.
            automation_interval: Period of the automation cycle.
            scenario_interval: Period of the scenario tick.

        Returns:
            None.
        """
        self._run_automation = run_automation
        self._tick_scenarios = tick_scenarios
        self._automation_interval = automation_interval
        self._scenario_interval = scenario_interval
        self._tasks: list[asyncio.Task] = []
        self._stop = asyncio.Event()

    async def start(self) -> None:
        """Start both background loops.

        Returns:
            None.
        """
        self._stop.clear()
        self._tasks = [
            asyncio.create_task(
                self._loop(self._automation_cycle, self._automation_interval, "automation")
            ),
            asyncio.create_task(
                self._loop(self._scenario_cycle, self._scenario_interval, "scenarios")
            ),
        ]
        log.info("Background scheduler started")

    async def stop(self) -> None:
        """Stop both background loops.

        Returns:
            None.
        """
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks = []
        log.info("Background scheduler stopped")

    async def _loop(self, cycle: Callable[[], Awaitable[None]], interval: float, name: str) -> None:
        """Run a cycle forever, sleeping between iterations.

        A failing iteration is logged and retried on the next tick instead of
        killing the loop.

        Args:
            cycle: Coroutine function performing one iteration.
            interval: Sleep between iterations in seconds.
            name: Loop name used in log records.

        Returns:
            None.
        """
        while not self._stop.is_set():
            try:
                await cycle()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("scheduler loop failed", extra={"ctx": {"loop": name, "error": str(exc)}})
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=interval)

    async def _automation_cycle(self) -> None:
        await self._run_automation.execute()

    async def _scenario_cycle(self) -> None:
        await self._tick_scenarios.execute()
