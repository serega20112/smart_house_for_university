"""Словарь отказов домена.

Здесь только инварианты: значения, которые модель отказывается держать, и
переходы, которые она отказывается сделать. Отказ из внешнего мира принадлежит тому
слою, который с этим миром и разговаривает: неподошедший хэш пароля — ошибка
приложения, а занятый логин — ограничение хранилища.

Каждая ошибка несёт контекст, которым отказ можно объяснить человеку, а
presentation превращает тип в код ответа, а не наоборот.
"""

from backend.domain.exceptions.accounts import (
    InvalidDisplayNameError,
    InvalidEmailError,
    WeakPasswordError,
)
from backend.domain.exceptions.base import DomainError
from backend.domain.exceptions.boards import (
    ClaimAlreadyTakenError,
    ClaimExpiredError,
    InvalidBoardNameError,
    InvalidNetworkProfileError,
    InvalidPairingKeyError,
)
from backend.domain.exceptions.climate import (
    InvalidHumidityError,
    InvalidMeasurementError,
    InvalidTemperatureError,
    InvalidToleranceError,
)
from backend.domain.exceptions.devices import (
    ChannelConflictError,
    InvalidCapabilityError,
    InvalidDeviceKindError,
    InvalidDeviceNameError,
    InvalidRelayChannelError,
    UnsupportedCapabilityError,
)
from backend.domain.exceptions.identity import MalformedIdentifierError
from backend.domain.exceptions.personalization import (
    DashboardAccessDeniedError,
    InvalidDashboardLayoutError,
    InvalidWidgetKindError,
)
from backend.domain.exceptions.scenarios import (
    IllegalScenarioTransitionError,
    InvalidCompletionBehaviorError,
    InvalidScenarioTargetError,
    ScenarioAlreadyFinishedError,
)

__all__ = [
    "ChannelConflictError",
    "ClaimAlreadyTakenError",
    "ClaimExpiredError",
    "DashboardAccessDeniedError",
    "DomainError",
    "IllegalScenarioTransitionError",
    "InvalidBoardNameError",
    "InvalidCapabilityError",
    "InvalidCompletionBehaviorError",
    "InvalidDashboardLayoutError",
    "InvalidDeviceKindError",
    "InvalidDeviceNameError",
    "InvalidDisplayNameError",
    "InvalidEmailError",
    "InvalidHumidityError",
    "InvalidMeasurementError",
    "InvalidNetworkProfileError",
    "InvalidPairingKeyError",
    "InvalidRelayChannelError",
    "InvalidScenarioTargetError",
    "InvalidTemperatureError",
    "InvalidToleranceError",
    "InvalidWidgetKindError",
    "MalformedIdentifierError",
    "ScenarioAlreadyFinishedError",
    "UnsupportedCapabilityError",
    "WeakPasswordError",
]
