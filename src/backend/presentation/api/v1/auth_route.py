"""Маршруты регистрации, входа и выхода.

Это единственные ручки, которым не нужна сессия: они её и заводят. Всё остальное
начинается с аккаунта, разрешённого из bearer-токена.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from backend.application.errors import AccountNotFoundError
from backend.application.interfaces.queries.account_queries import AccountQueries
from backend.application.use_cases.accounts.authenticate_account import (
    AuthenticateAccountUseCase,
)
from backend.application.use_cases.accounts.register_account import RegisterAccountUseCase
from backend.presentation.api.requests.auth import (
    LoginBody,
    RegisterBody,
    authenticate_command,
    register_command,
)
from backend.presentation.api.responses.auth import (
    SessionResponse,
    UserResponse,
    profile_of,
    session_of,
)
from backend.presentation.api.responses.common import OperationResponse
from backend.presentation.messages import LOGGED_OUT
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=SessionResponse)
async def register(
    body: RegisterBody, use_case: FromDishka[RegisterAccountUseCase]
) -> SessionResponse:
    """Создаёт аккаунт и открывает для него сессию.

    Новый аккаунт сразу владеет своими устройствами, настройками и панелью,
    поэтому первый же ответ отдаёт полное персональное состояние дома.

    Args:
        body: Запрос на создание аккаунта.
        use_case: Создание аккаунта.

    Returns:
        SessionResponse: Профиль аккаунта и его токен сессии.
    """
    session = await use_case.execute(register_command(body))
    return session_of(session)


@router.post("/login", response_model=SessionResponse)
async def login(
    body: LoginBody, use_case: FromDishka[AuthenticateAccountUseCase]
) -> SessionResponse:
    """Авторизует аккаунт и выдаёт токен сессии.

    Args:
        body: Логин и пароль.
        use_case: Авторизация аккаунта.

    Returns:
        SessionResponse: Профиль аккаунта и его токен сессии.
    """
    session = await use_case.execute(authenticate_command(body))
    return session_of(session)


@router.post("/logout", response_model=OperationResponse)
async def logout() -> OperationResponse:
    """Закрывает текущую сессию.

    Токены не хранятся, поэтому сессия заканчивается в тот момент, когда клиент
    перестаёт держать токен. Ручка существует, чтобы у клиента было одно
    очевидное место, где его забыть.

    Returns:
        OperationResponse: Подтверждение выхода.
    """
    return OperationResponse(status="ok", message=LOGGED_OUT)


@router.get("/me", response_model=UserResponse)
async def read_session(user_id: CurrentUserId, queries: FromDishka[AccountQueries]) -> UserResponse:
    """Возвращает аккаунт текущей сессии.

    Args:
        user_id: Владелец, разрешённый из bearer-токена.
        queries: Дешёвые чтения аккаунтов.

    Returns:
        UserResponse: Профиль вошедшего аккаунта.

    Raises:
        AccountNotFoundError: Когда аккаунт с таким токеном исчез.
    """
    profile = await queries.get_profile(user_id)
    if profile is None:
        raise AccountNotFoundError(user_id)
    return profile_of(profile)
