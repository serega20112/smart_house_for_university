"""Registration, authorization and logout routes.

These are the only endpoints that do not need a session, because they are the
ones that establish it. Everything else starts from the account resolved out of
the bearer token.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from smart_home.application.dto import (
    AuthenticateCommand,
    RegisterAccountCommand,
)
from smart_home.application.errors import AccountNotFoundError
from smart_home.application.ports.queries.accounts import AccountQueries
from smart_home.application.use_cases.accounts.authenticate_account import (
    AuthenticateAccountUseCase,
)
from smart_home.application.use_cases.accounts.register_account import (
    RegisterAccountUseCase,
)
from smart_home.presentation.api.messages import LOGGED_OUT
from smart_home.presentation.api.schemas import (
    LoginBody,
    OperationResponse,
    RegisterBody,
    SessionResponse,
    UserResponse,
    profile_of,
    session_of,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=SessionResponse)
async def register(
    body: RegisterBody, use_case: FromDishka[RegisterAccountUseCase]
) -> SessionResponse:
    """Create an account and start a session for it.

    The new account immediately owns its own devices, preferences and dashboard,
    so the very first response already is a complete personalized state.

    Args:
        body: Registration request.
        use_case: Account creation.

    Returns:
        SessionResponse: Account profile and its session token.
    """
    session = await use_case.execute(
        RegisterAccountCommand(
            email=body.email,
            display_name=body.display_name,
            password=body.password,
        )
    )
    return session_of(session)


@router.post("/login", response_model=SessionResponse)
async def login(
    body: LoginBody, use_case: FromDishka[AuthenticateAccountUseCase]
) -> SessionResponse:
    """Authorize an account and issue a session token.

    Args:
        body: Login and password.
        use_case: Authorization of an account.

    Returns:
        SessionResponse: Account profile and its session token.
    """
    session = await use_case.execute(AuthenticateCommand(email=body.email, password=body.password))
    return session_of(session)


@router.post("/logout", response_model=OperationResponse)
async def logout() -> OperationResponse:
    """End the current session.

    Tokens are stateless, so the session ends the moment the client drops the
    token. The endpoint exists so a client has one obvious place to forget it.

    Returns:
        OperationResponse: Acknowledgement of the logout.
    """
    return OperationResponse(status="ok", message=LOGGED_OUT)


@router.get("/me", response_model=UserResponse)
async def read_session(user_id: CurrentUserId, queries: FromDishka[AccountQueries]) -> UserResponse:
    """Return the account of the current session.

    Args:
        user_id: Owner resolved from the bearer token.
        queries: Cheap reads of the accounts.

    Returns:
        UserResponse: Profile of the signed in account.
    """
    profile = await queries.get_profile(user_id)
    if profile is None:
        raise AccountNotFoundError(user_id)
    return profile_of(profile)
