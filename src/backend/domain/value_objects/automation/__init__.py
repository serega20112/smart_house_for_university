"""Значения автоматизации: отчёт цикла.

Барель переэкспортирует только доменные значения; модель чтения автоматизации
(`AutomationView`) переехала в прикладной слой, чтобы домен не знал про форму экрана.
"""

from backend.domain.value_objects.automation.automation_cycle_report import (
    AutomationCycleReport,
)

__all__ = ["AutomationCycleReport"]
