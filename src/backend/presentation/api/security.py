"""Resolution of the current user from the request.

Authorization is derived from the session token and from nothing else. A user
identifier travelling in a body or a query string is never read, so replacing it
only changes an argument the server ignores.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.domain.value_objects.identity import UserId
from backend.infrastructure.di import Container
from backend.presentation.dependencies import get_container

bearer_scheme = HTTPBearer(auto_error=False)

UNAUTHORIZED = "Требуется авторизация"
CREDENTIALS_HEADERS = {"WWW-Authenticate": "Bearer"}


def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserId:
    """Resolve the account the request was authorized as.

    Args:
        request: Incoming request carrying the dependency container.
        credentials: Bearer token presented by the client.

    Returns:
        UserId: Owner the token was issued for.

    Raises:
        HTTPException: When the token is missing, unknown or expired.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED,
            headers=CREDENTIALS_HEADERS,
        )
    container: Container = get_container(request)
    user_id = container.tokens.resolve(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED,
            headers=CREDENTIALS_HEADERS,
        )
    return user_id


CurrentUserId = Annotated[UserId, Depends(get_current_user_id)]
AppContainer = Annotated[Container, Depends(get_container)]
