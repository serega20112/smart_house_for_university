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


class InvalidScenarioTargetError(DomainError):
    """Названное место или предмет не помещается в модель сценария.

    Attributes:
        length: Длина названного значения после обрезки пробелов.
        limit: Сколько символов модель разрешает.
    """

    def __init__(self, length: int, limit: int) -> None:
        """Запоминает длину значения и предел модели.

        Args:
            length: Длина названного значения после обрезки пробелов.
            limit: Сколько символов модель разрешает.
        """
        super().__init__(f"scenario target is {length} characters long, limit is {limit}")
        self.length = length
        self.limit = limit


class InvalidCompletionBehaviorError(DomainError):
    """Значение не называет поведение завершения сценария.

    Attributes:
        raw: Отвергнутое значение.
    """

    def __init__(self, raw: object) -> None:
        """Запоминает отвергнутое значение.

        Args:
            raw: Отвергнутое значение.
        """
        super().__init__(f"unknown scenario completion behavior: {raw!r}")
        self.raw = raw
