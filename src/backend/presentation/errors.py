"""Перевод сбоев внутренних слоёв в ответы интерфейсов.

Коды состояния всего API решаются здесь и больше нигде. Каждый слой ниже бросает
исключение, описывающее неисправность на языке домена или прикладного слоя, а эта
таблица — единственное место, где сбой получает код и фразу, которую человек
может прочитать.

Фразу отсюда же берёт и интерфейс мессенджера: один и тот же сбой не может
в HTTP означать одно, а в чате другое.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.application import errors
from backend.domain import exceptions as domain_errors
from backend.presentation.messages import (
    BOARD_UNREACHABLE,
    CHANNEL_CONFLICT,
    CLAIM_EXPIRED,
    CLAIM_MISSING,
    CLAIM_TAKEN,
    COMMAND_NOT_UNDERSTOOD,
    DEVICE_MISSING,
    EMAIL_TAKEN,
    INTERNAL_FAILURE,
    INVALID_CREDENTIALS,
    INVALID_DASHBOARD_LAYOUT,
    INVALID_DEVICE_NAME,
    INVALID_EMAIL,
    INVALID_NAME,
    INVALID_NETWORK_PROFILE,
    INVALID_PAIRING_KEY,
    INVALID_RELAY_CHANNEL,
    INVALID_TEMPERATURE,
    MALFORMED_IDENTIFIER,
    SCENARIO_ALREADY_FINISHED,
    SCENARIO_MISSING,
    UNSUPPORTED_CAPABILITY,
    WEAK_PASSWORD,
    error_detail,
)

UNPROCESSABLE = status.HTTP_422_UNPROCESSABLE_CONTENT
SERVER_FAILURE = status.HTTP_500_INTERNAL_SERVER_ERROR

APPLICATION_STATUSES: dict[type[BaseException], tuple[int, str]] = {
    errors.InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS),
    errors.EmailAlreadyTakenError: (status.HTTP_409_CONFLICT, EMAIL_TAKEN),
    errors.DeviceNotFoundError: (status.HTTP_404_NOT_FOUND, DEVICE_MISSING),
    errors.ScenarioNotFoundError: (status.HTTP_404_NOT_FOUND, SCENARIO_MISSING),
    errors.BoardNotFoundError: (status.HTTP_404_NOT_FOUND, DEVICE_MISSING),
    errors.ClaimNotFoundError: (status.HTTP_404_NOT_FOUND, CLAIM_MISSING),
    errors.NoDeviceForCapabilityError: (status.HTTP_404_NOT_FOUND, DEVICE_MISSING),
    errors.BoardAlreadyClaimedError: (status.HTTP_409_CONFLICT, CLAIM_TAKEN),
    errors.BoardUnreachableError: (status.HTTP_502_BAD_GATEWAY, BOARD_UNREACHABLE),
    errors.CommandNotUnderstoodError: (UNPROCESSABLE, COMMAND_NOT_UNDERSTOOD),
}

DOMAIN_STATUSES: dict[type[BaseException], tuple[int, str]] = {
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
        SCENARIO_ALREADY_FINISHED,
    ),
    domain_errors.InvalidEmailError: (UNPROCESSABLE, INVALID_EMAIL),
    domain_errors.InvalidDisplayNameError: (UNPROCESSABLE, INVALID_NAME),
    domain_errors.WeakPasswordError: (UNPROCESSABLE, WEAK_PASSWORD),
    domain_errors.InvalidDeviceNameError: (UNPROCESSABLE, INVALID_DEVICE_NAME),
    domain_errors.InvalidRelayChannelError: (UNPROCESSABLE, INVALID_RELAY_CHANNEL),
    domain_errors.InvalidTemperatureError: (UNPROCESSABLE, INVALID_TEMPERATURE),
    domain_errors.InvalidPairingKeyError: (UNPROCESSABLE, INVALID_PAIRING_KEY),
    domain_errors.InvalidNetworkProfileError: (UNPROCESSABLE, INVALID_NETWORK_PROFILE),
    domain_errors.InvalidDashboardLayoutError: (UNPROCESSABLE, INVALID_DASHBOARD_LAYOUT),
    domain_errors.MalformedIdentifierError: (status.HTTP_400_BAD_REQUEST, MALFORMED_IDENTIFIER),
}

FAILURE_TABLES: tuple[dict[type[BaseException], tuple[int, str]], ...] = (
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
        for error_type, decision in table.items():
            if isinstance(error, error_type):
                return decision
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
