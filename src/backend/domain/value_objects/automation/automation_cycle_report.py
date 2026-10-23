"""Итог одного цикла автоматизации."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.value_objects.climate.skip_reason import SkipReason


@dataclass(frozen=True, slots=True)
class AutomationCycleReport:
    """Каждое требование цикла и то, чем оно закончилось.

    На каждое требование, выданное калькулятором, приходится ровно одна запись в
    `performed`, `failed` или `skipped`, поэтому цикл, выполнивший три требования
    и споткнувшийся на четвёртом, всё равно отчитается по всем и по порядку.
    Когда требование вообще не было выдано, объяснение лежит в `cycle_skipped`.

    Attributes:
        performed: Требования, которые выполнили.
        failed: Требования, которые не удалось выполнить, вместе с причиной.
        skipped: Требования, которые пропустили, вместе с причиной.
        cycle_skipped: Почему цикл ничего не сделал, или None, если он действовал.
    """

    performed: tuple[str, ...] = ()
    failed: tuple[tuple[str, str], ...] = ()
    skipped: tuple[tuple[str, str], ...] = ()
    cycle_skipped: SkipReason | None = None
