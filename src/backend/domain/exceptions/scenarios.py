"""Отказы сценариев."""

from __future__ import annotations

from backend.domain.exceptions.base import DomainError


class ScenarioAlreadyFinishedError(DomainError):
    """Сценарий в финальной стадии нельзя отменить или завершить ещё раз.

    Attributes:
        scenario_id: Идентификатор сценария.
        status: Стадия, на которой он уже находится.
    """

    def __init__(self, scenario_id: str, status: str) -> None:
        """Запоминает идентификатор и достигнутую стадию.

        Args:
            scenario_id: Идентификатор сценария.
            status: Стадия, на которой он уже находится.
        """
        super().__init__(f"scenario {scenario_id} is already {status}")
        self.scenario_id = scenario_id
        self.status = status


class IllegalScenarioTransitionError(DomainError):
    """Сценарию предложили переход между стадиями, которые не идут подряд.

    Attributes:
        scenario_id: Идентификатор сценария.
        current: Текущая стадия.
        requested: Затребованная стадия.
    """

    def __init__(self, scenario_id: str, current: str, requested: str) -> None:
        """Запоминает идентификатор и оба состояния перехода.

        Args:
            scenario_id: Идентификатор сценария.
            current: Текущая стадия.
            requested: Затребованная стадия.
        """
        super().__init__(f"scenario {scenario_id} cannot go from {current} to {requested}")
        self.scenario_id = scenario_id
        self.current = current
        self.requested = requested
