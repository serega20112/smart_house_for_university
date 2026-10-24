"""Насколько измерение может отойти от своей цели.

Допуск — объект-значение, а не голое число: отрицательный допуск это не «очень
маленький допуск», а коридор, который невозможно достичь, а его знак легко потерять,
пока число идёт через сценарий приложения. Объект отвергает невозможное значение один
раз, при построении, и после этого носит его спокойно.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import InvalidToleranceError

MAX_TOLERANCE = 50.0
"""Самый большой допуск, который может нести любое измерение."""


@dataclass(frozen=True, slots=True)
class Tolerance:
    """Насколько измерение может отойти от своей цели.

    Attributes:
        value: Ширина допустимого коридора, никогда не отрицательная.
    """

    value: float

    def __post_init__(self) -> None:
        """Проверяет ширину коридора.

        Raises:
            InvalidToleranceError: Когда ширина отрицательная или слишком большая.
        """
        if self.value < 0:
            raise InvalidToleranceError(self.value)
        if self.value > MAX_TOLERANCE:
            raise InvalidToleranceError(self.value)

    def __float__(self) -> float:
        """Возвращает ширину коридора."""
        return self.value
