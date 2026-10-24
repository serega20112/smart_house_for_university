"""Маршруты регистрации, входа и выхода.

Это ручки, которые заводят сессию: всё остальное начинается с аккаунта, разрешённого
из bearer-токена. Без токена доступны ещё только служебные `health`, `ready` и
`metrics` — они говорят о процессе, а не о доме, и живут в соседнем модуле.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from backend.application.errors import AccountNotFoundError
from backend.application.interfaces.queries.account_queries import AccountQueries
from backend.application.interfaces.services.security.realtime_ticket_store import (
    RealtimeTicketStore,
)
from backend.application.use_cases.accounts.authenticate_account import (
    AuthenticateAccountUseCase,
)
from backend.application.use_cases.accounts.register_account import RegisterAccountUseCase
from backend.config.settings import Settings
from backend.presentation.api.requests.auth import (
    LoginBody,
    RegisterBody,
    authenticate_command,
    register_command,
)
from backend.presentation.api.responses.auth import (
    RealtimeTicketResponse,
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

    Новый аккаунт сразу владеет устройствами, настройками и панелью: их заводит сама
    регистрация. Ответ несёт только профиль и токен, потому что снимок дома —
    отдельное чтение `/api/state` под этим токеном, а не часть ответа о создании
    аккаунта.

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


@router.post("/realtime-ticket", response_model=RealtimeTicketResponse)
async def realtime_ticket(
    user_id: CurrentUserId,
    tickets: FromDishka[RealtimeTicketStore],
    settings: FromDishka[Settings],
) -> RealtimeTicketResponse:
    """Выдаёт одноразовый билет, которым интерфейс откроет WebSocket.

    Держать токен сессии в строке запроса соединения нельзя: адрес попадает в логи и
    историю. Поэтому под текущей сессией выдаётся короткий билет, который WebSocket
    обменяет на аккаунт ровно один раз.

    Args:
        user_id: Владелец, разрешённый из bearer-токена.
        tickets: Хранилище одноразовых билетов.
        settings: Конфигурация, задающая срок жизни билета.

    Returns:
        RealtimeTicketResponse: Билет и число секунд его жизни.
    """
    ticket = await tickets.issue(user_id)
    return RealtimeTicketResponse(ticket=ticket, expires_in_sec=settings.realtime_ticket_ttl_sec)
