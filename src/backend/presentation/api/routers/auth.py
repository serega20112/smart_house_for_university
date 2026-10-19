"""Registration, authorization and logout routes.

These are the only endpoints that do not need a session, because they are the
ones that establish it. Everything else starts from the account resolved out of
the bearer token.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.application.dto.user import (
    AuthenticateUserCommand,
    RegisterUserCommand,
)
from backend.domain.entities.user import (
    InvalidDisplayNameError,
    InvalidEmailError,
)
from backend.domain.exceptions import (
    EmailAlreadyTakenError,
    InvalidCredentialsError,
    WeakPasswordError,
)
from backend.presentation.api.requests import (
    LoginBody,
    RegisterBody,
)
from backend.presentation.api.responses import (
    SessionResponse,
    UserResponse,
    error_detail,
)
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_TAKEN = "Этот email уже зарегистрирован"
INVALID_CREDENTIALS = "Неверный email или пароль"
INVALID_EMAIL = "Некорректный email"
INVALID_NAME = "Некорректное имя"
WEAK_PASSWORD = "Пароль слишком короткий"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterBody, container: AppContainer) -> SessionResponse:
    """Create an account and start a session for it.

    The new account immediately owns its own devices, preferences and dashboard,
    so the very first response already is a complete personalized state.

    Args:
        body: Registration request.
        container: Assembled dependency graph.

    Returns:
        SessionResponse: Account profile and its session token.

    Raises:
        HTTPException: When the login is taken or the request is malformed.
    """
    try:
        session = await container.register_user.execute(
            RegisterUserCommand(
                email=body.email, password=body.password, display_name=body.display_name
            )
        )
    except EmailAlreadyTakenError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, error_detail(EMAIL_TAKEN)) from exc
    except InvalidEmailError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, error_detail(INVALID_EMAIL)
        ) from exc
    except InvalidDisplayNameError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, error_detail(INVALID_NAME)
        ) from exc
    except WeakPasswordError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, error_detail(WEAK_PASSWORD)
        ) from exc
    return SessionResponse.from_session(session)


@router.post("/login")
async def login(body: LoginBody, container: AppContainer) -> SessionResponse:
    """Authorize an account and issue a session token.

    Args:
        body: Login and password.
        container: Assembled dependency graph.

    Returns:
        SessionResponse: Account profile and its session token.

    Raises:
        HTTPException: When the credentials do not match an account.
    """
    try:
        session = await container.authenticate_user.execute(
            AuthenticateUserCommand(email=body.email, password=body.password)
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, error_detail(INVALID_CREDENTIALS)
        ) from exc
    return SessionResponse.from_session(session)


@router.post("/logout")
async def logout() -> dict[str, str]:
    """End the current session.

    Tokens are stateless, so the session ends the moment the client drops the
    token. The endpoint exists so a client has one obvious place to forget it.

    Returns:
        dict[str, str]: Acknowledgement of the logout.
    """
    return {"status": "SUCCESS", "message": "Сессия завершена"}


@router.get("/me")
async def read_session(user_id: CurrentUserId, container: AppContainer) -> UserResponse:
    """Return the account of the current session.

    Args:
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        UserResponse: Profile of the signed in account.

    Raises:
        HTTPException: When the account no longer exists.
    """
    user = await container.get_current_user.execute(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, error_detail("Аккаунт не найден"))
    return UserResponse.from_user(user)
