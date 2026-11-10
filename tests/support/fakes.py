"""Двойники портов, на которых проверяются сценарии."""

from __future__ import annotations

from typing import Any

from backend.application.interfaces.unit_of_work.home import HomeUnitOfWork


class FakeUnitOfWork(HomeUnitOfWork):
    """Единица работы, отдающая заранее заготовленные двойники репозиториев.

    Репозитории передаются по имени класса порта, поэтому тест описывает только
    те порты, которые сценарий действительно запрашивает.
    """

    def __init__(self, **repositories: Any) -> None:
        """Создать двойник с репозиториями по именам портов.

        Args:
            **repositories: Двойники репозиториев, ключ — имя класса порта.
        """
        self._repositories = repositories
        self.commits = 0
        self.rollbacks = 0

    @property
    def devices(self) -> Any:
        """Репозиторий устройств текущей транзакции."""
        return self._repositories.get("DeviceRepository")

    @property
    def boards(self) -> Any:
        """Репозиторий плат текущей транзакции."""
        return self._repositories.get("BoardRepository")

    @property
    def automation(self) -> Any:
        """Репозиторий настроек автоматизации текущей транзакции."""
        return self._repositories.get("AutomationRepository")

    @property
    def scenarios(self) -> Any:
        """Репозиторий сценариев текущей транзакции."""
        return self._repositories.get("ScenarioRepository")

    @property
    def dashboard(self) -> Any:
        """Репозиторий раскладки панели текущей транзакции."""
        return self._repositories.get("DashboardRepository")

    @property
    def preferences(self) -> Any:
        """Репозиторий настроек интерфейса текущей транзакции."""
        return self._repositories.get("PreferencesRepository")

    async def commit(self) -> None:
        """Зафиксировать транзакцию в двойнике, только считая вызовы."""
        self.commits += 1

    async def rollback(self) -> None:
        """Отменить транзакцию в двойнике, только считая вызовы."""
        self.rollbacks += 1
