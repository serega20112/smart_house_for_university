"""Перевод сбоев внутренних слоёв в ответы интерфейсов.

Коды состояния всего API решаются здесь и больше нигде. Каждый слой ниже бросает
исключение, описывающее неисправность на языке домена или прикладного слоя, а эта
таблица — единственное место, где сбой получает код и фразу, которую человек
может прочитать.

Фразу отсюда же берёт и интерфейс мессенджера: один и тот же сбой не может
в HTTP означать одно, а в чате другое.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.application import errors
from backend.domain import exceptions as domain_errors
from backend.presentation.messages import (
    BOARD_HAS_DEVICES,
    BOARD_MISSING,
    BOARD_NOT_CHOSEN,
    BOARD_UNREACHABLE,
    CAPABILITY_UNSUPPORTED,
    CHANNEL_CONFLICT,
    CLAIM_EXPIRED,
    CLAIM_MISSING,
    CLAIM_TAKEN,
    COMMAND_NOT_UNDERSTOOD,
    DASHBOARD_ACCESS_DENIED,
    DEVICE_MISSING,
    EMAIL_TAKEN,
    ILLEGAL_SCENARIO_TRANSITION,
    INTERNAL_FAILURE,
    INVALID_BOARD_NAME,
    INVALID_CAPABILITY,
    INVALID_COMPLETION_BEHAVIOR,
    INVALID_CREDENTIALS,
    INVALID_DASHBOARD_LAYOUT,
    INVALID_DEVICE_KIND,
    INVALID_DEVICE_NAME,
    INVALID_EMAIL,
    INVALID_HUMIDITY,
    INVALID_NAME,
    INVALID_NETWORK_PROFILE,
    INVALID_PAIRING_KEY,
    INVALID_RELAY_CHANNEL,
    INVALID_SCENARIO_TARGET,
    INVALID_TEMPERATURE,
    INVALID_TOLERANCE,
    INVALID_WIDGET_KIND,
    LANGUAGE_MODEL_UNAVAILABLE,
    MALFORMED_IDENTIFIER,
    SCENARIO_ALREADY_FINISHED,
    SCENARIO_MISSING,
    SESSION_OWNER_MISSING,
    STATE_CHANGED,
    UNSUPPORTED_CAPABILITY,
    WEAK_PASSWORD,
    error_detail,
)

UNPROCESSABLE = status.HTTP_422_UNPROCESSABLE_CONTENT
SERVER_FAILURE = status.HTTP_500_INTERNAL_SERVER_ERROR

Message = str | Callable[[BaseException], str]
FailureTable = dict[type[BaseException], tuple[int, Message]]


def board_has_devices(error: BaseException) -> str:
    """Возвращает фразу о плате, за которой ещё стоят устройства.

    Перечень берётся из самого сбоя: сколько устройств у платы, знает только он.

    Args:
        error: Сбой, несущий имена этих устройств.

    Returns:
        str: Фраза с перечнем устройств.
    """
    devices = error.devices if isinstance(error, errors.BoardHasDevicesError) else ()
    return BOARD_HAS_DEVICES.format(devices=", ".join(devices))


APPLICATION_STATUSES: FailureTable = {
    errors.InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS),
    errors.AccountNotFoundError: (status.HTTP_401_UNAUTHORIZED, SESSION_OWNER_MISSING),
    errors.EmailAlreadyTakenError: (status.HTTP_409_CONFLICT, EMAIL_TAKEN),
    errors.DeviceNotFoundError: (status.HTTP_404_NOT_FOUND, DEVICE_MISSING),
    errors.ScenarioNotFoundError: (status.HTTP_404_NOT_FOUND, SCENARIO_MISSING),
    errors.BoardNotFoundError: (status.HTTP_404_NOT_FOUND, BOARD_MISSING),
    errors.BoardHasDevicesError: (status.HTTP_409_CONFLICT, board_has_devices),
    errors.ClaimNotFoundError: (status.HTTP_404_NOT_FOUND, CLAIM_MISSING),
    errors.NoDeviceForCapabilityError: (status.HTTP_404_NOT_FOUND, CAPABILITY_UNSUPPORTED),
    errors.BoardAlreadyClaimedError: (status.HTTP_409_CONFLICT, CLAIM_TAKEN),
    errors.ConcurrentModificationError: (status.HTTP_409_CONFLICT, STATE_CHANGED),
    errors.BoardNotChosenError: (status.HTTP_409_CONFLICT, BOARD_NOT_CHOSEN),
    errors.BoardUnreachableError: (status.HTTP_502_BAD_GATEWAY, BOARD_UNREACHABLE),
    errors.CommandNotUnderstoodError: (UNPROCESSABLE, COMMAND_NOT_UNDERSTOOD),
    errors.LanguageModelUnavailable: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        LANGUAGE_MODEL_UNAVAILABLE,
    ),
    errors.RemoteUnderstandingUnavailable: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        LANGUAGE_MODEL_UNAVAILABLE,
    ),
}

DOMAIN_STATUSES: FailureTable = {
    domain_errors.ChannelConflictError: (status.HTTP_409_CONFLICT, CHANNEL_CONFLICT),
    domain_errors.ClaimAlreadyTakenError: (status.HTTP_409_CONFLICT, CLAIM_TAKEN),
    domain_errors.ClaimExpiredError: (status.HTTP_410_GONE, CLAIM_EXPIRED),
    domain_errors.UnsupportedCapabilityError: (UNPROCESSABLE, UNSUPPORTED_CAPABILITY),
    domain_errors.ScenarioAlreadyFinishedError: (
        status.HTTP_409_CONFLICT,
        SCENARIO_ALREADY_FINISHED,
    ),
    domain_errors.IllegalScenarioTransitionError: (
        status.HTTP_409_CONFLICT,
        ILLEGAL_SCENARIO_TRANSITION,
    ),
    domain_errors.InvalidEmailError: (UNPROCESSABLE, INVALID_EMAIL),
    domain_errors.InvalidDisplayNameError: (UNPROCESSABLE, INVALID_NAME),
    domain_errors.WeakPasswordError: (UNPROCESSABLE, WEAK_PASSWORD),
    domain_errors.InvalidBoardNameError: (UNPROCESSABLE, INVALID_BOARD_NAME),
    domain_errors.InvalidDeviceNameError: (UNPROCESSABLE, INVALID_DEVICE_NAME),
    domain_errors.InvalidDeviceKindError: (UNPROCESSABLE, INVALID_DEVICE_KIND),
    domain_errors.InvalidCapabilityError: (UNPROCESSABLE, INVALID_CAPABILITY),
    domain_errors.InvalidRelayChannelError: (UNPROCESSABLE, INVALID_RELAY_CHANNEL),
    domain_errors.InvalidTemperatureError: (UNPROCESSABLE, INVALID_TEMPERATURE),
    domain_errors.InvalidHumidityError: (UNPROCESSABLE, INVALID_HUMIDITY),
    domain_errors.InvalidToleranceError: (UNPROCESSABLE, INVALID_TOLERANCE),
    domain_errors.InvalidCompletionBehaviorError: (UNPROCESSABLE, INVALID_COMPLETION_BEHAVIOR),
    domain_errors.InvalidScenarioTargetError: (UNPROCESSABLE, INVALID_SCENARIO_TARGET),
    domain_errors.InvalidPairingKeyError: (UNPROCESSABLE, INVALID_PAIRING_KEY),
    domain_errors.InvalidNetworkProfileError: (UNPROCESSABLE, INVALID_NETWORK_PROFILE),
    domain_errors.InvalidDashboardLayoutError: (UNPROCESSABLE, INVALID_DASHBOARD_LAYOUT),
    domain_errors.InvalidWidgetKindError: (UNPROCESSABLE, INVALID_WIDGET_KIND),
    domain_errors.DashboardAccessDeniedError: (
        status.HTTP_403_FORBIDDEN,
        DASHBOARD_ACCESS_DENIED,
    ),
    domain_errors.MalformedIdentifierError: (status.HTTP_400_BAD_REQUEST, MALFORMED_IDENTIFIER),
    domain_errors.InvalidMeasurementError: (SERVER_FAILURE, INTERNAL_FAILURE),
}

FAILURE_TABLES: tuple[FailureTable, ...] = (
    APPLICATION_STATUSES,
    DOMAIN_STATUSES,
)


def describe(error: BaseException) -> tuple[int, str]:
    """Возвращает код и фразу, которыми интерфейс отвечает на этот сбой.

    Неизвестный сбой получает внутреннюю ошибку: молча превратить его в успешный
    ответ нельзя, а придумать ему фразу здесь значило бы скрыть дефект.

    Args:
        error: Сбой, который поднялся.

    Returns:
        tuple[int, str]: Код ответа и фраза для человека.
    """
    for table in FAILURE_TABLES:
        for error_type, (code, message) in table.items():
            if isinstance(error, error_type):
                return code, message(error) if callable(message) else message
    return SERVER_FAILURE, INTERNAL_FAILURE


def answer_of(error: BaseException) -> JSONResponse:
    """Собирает тело ответа HTTP по поднявшемуся сбою.

    Args:
        error: Сбой, который поднялся.

    Returns:
        JSONResponse: Ответ запроса.
    """
    code, message = describe(error)
    return JSONResponse(status_code=code, content=error_detail(message))


def install_error_handlers(app: FastAPI) -> None:
    """Учит приложение отвечать на сбои внутренних слоёв собранной таблицей.

    Args:
        app: Приложение, к которому подвязывают обработчики.
    """

    @app.exception_handler(errors.ApplicationError)
    async def handle_application_error(
        request: Request, error: errors.ApplicationError
    ) -> JSONResponse:
        """Отвечает на сбой прикладного слоя.

        Args:
            request: Запрос, на котором сбой случился.
            error: Поднявшийся сбой.

        Returns:
            JSONResponse: Ответ запроса.
        """
        del request
        return answer_of(error)

    @app.exception_handler(domain_errors.DomainError)
    async def handle_domain_error(
        request: Request, error: domain_errors.DomainError
    ) -> JSONResponse:
        """Отвечает на сбой доменного слоя.

        Args:
            request: Запрос, на котором сбой случился.
            error: Поднявшийся сбой.

        Returns:
            JSONResponse: Ответ запроса.
        """
        del request
        return answer_of(error)
