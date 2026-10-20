"""Translation of the failures of the application into HTTP answers.

The status codes of the whole API are decided in this module and nowhere else.
Every other layer raises exceptions that describe what went wrong in the language
of the domain or of the application, and this table is the single place where
those failures are given a code and a sentence a person can read.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from smart_home.application import errors
from smart_home.presentation.api.messages import (
    BOARD_UNREACHABLE,
    CHANNEL_CONFLICT,
    CLAIM_EXPIRED,
    CLAIM_MISSING,
    CLAIM_TAKEN,
    COMMAND_NOT_UNDERSTOOD,
    DEVICE_MISSING,
    EMAIL_TAKEN,
    INVALID_CREDENTIALS,
    SCENARIO_ALREADY_FINISHED,
    SCENARIO_MISSING,
    UNSUPPORTED_CAPABILITY,
    error_detail,
)

APPLICATION_STATUSES: dict[type[BaseException], tuple[int, str]] = {
    errors.InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS),
    errors.EmailAlreadyTakenError: (status.HTTP_409_CONFLICT, EMAIL_TAKEN),
    errors.DeviceNotFoundError: (status.HTTP_404_NOT_FOUND, DEVICE_MISSING),
    errors.ScenarioNotFoundError: (status.HTTP_404_NOT_FOUND, SCENARIO_MISSING),
    errors.BoardNotFoundError: (status.HTTP_404_NOT_FOUND, DEVICE_MISSING),
    errors.ClaimNotFoundError: (status.HTTP_404_NOT_FOUND, CLAIM_MISSING),
    errors.BoardUnreachableError: (status.HTTP_502_BAD_GATEWAY, BOARD_UNREACHABLE),
    errors.CommandNotUnderstoodError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        COMMAND_NOT_UNDERSTOOD,
    ),
}

DOMAIN_STATUSES: dict[type[BaseException], tuple[int, str]] = {
    errors.ChannelConflictError: (status.HTTP_409_CONFLICT, CHANNEL_CONFLICT),
    errors.ClaimAlreadyTakenError: (status.HTTP_409_CONFLICT, CLAIM_TAKEN),
    errors.ClaimExpiredError: (status.HTTP_410_GONE, CLAIM_EXPIRED),
    errors.UnsupportedCapabilityError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        UNSUPPORTED_CAPABILITY,
    ),
    errors.NoDeviceForCapabilityError: (status.HTTP_404_NOT_FOUND, DEVICE_MISSING),
    errors.ScenarioAlreadyFinishedError: (
        status.HTTP_409_CONFLICT,
        SCENARIO_ALREADY_FINISHED,
    ),
    errors.IllegalScenarioTransitionError: (
        status.HTTP_409_CONFLICT,
        SCENARIO_ALREADY_FINISHED,
    ),
    errors.InvalidEmailError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Некорректный email."),
    errors.InvalidDisplayNameError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Некорректное имя.",
    ),
    errors.WeakPasswordError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Пароль слишком короткий.",
    ),
    errors.InvalidDeviceNameError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Некорректное имя устройства.",
    ),
    errors.InvalidRelayChannelError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Некорректный канал реле.",
    ),
    errors.InvalidTemperatureError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Некорректная температура.",
    ),
    errors.InvalidPairingKeyError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Некорректный ключ сопряжения.",
    ),
    errors.InvalidNetworkProfileError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Некорректные параметры сети.",
    ),
    errors.InvalidDashboardLayoutError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Некорректная раскладка панели.",
    ),
    errors.MalformedIdentifierError: (
        status.HTTP_400_BAD_REQUEST,
        "Некорректный идентификатор.",
    ),
}


def _answer(error: Exception, table: dict[type[BaseException], tuple[int, str]]) -> JSONResponse:
    """Return the answer of a failure found in a table.

    Args:
        error: Failure that was raised.
        table: Mapping of a failure type onto a status and a sentence.

    Returns:
        JSONResponse: Answer of the request.
    """
    for error_type, (code, message) in table.items():
        if isinstance(error, error_type):
            return JSONResponse(status_code=code, content=error_detail(message))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_detail("Внутренняя ошибка сервера."),
    )


def install_error_handlers(app: FastAPI) -> None:
    """Teach the application how to answer the failures of the inner layers.

    Args:
        app: Application the handlers are attached to.

    Returns:
        None.
    """

    @app.exception_handler(errors.ApplicationError)
    async def handle_application_error(
        request: Request, error: errors.ApplicationError
    ) -> JSONResponse:
        """Answer a failure of the application layer.

        Args:
            request: Request that failed.
            error: Failure that was raised.

        Returns:
            JSONResponse: Answer of the request.
        """
        del request
        return _answer(error, APPLICATION_STATUSES)

    @app.exception_handler(errors.DomainError)
    async def handle_domain_error(request: Request, error: errors.DomainError) -> JSONResponse:
        """Answer a failure of the domain layer.

        Args:
            request: Request that failed.
            error: Failure that was raised.

        Returns:
            JSONResponse: Answer of the request.
        """
        del request
        return _answer(error, DOMAIN_STATUSES)
