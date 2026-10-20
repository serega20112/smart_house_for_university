"""Resolution of the current account from the request.

Authorization is derived from the session token and from nothing else. An account
identifier travelling in a body or in a query string is never read, so replacing
it only changes an argument the server ignores.
"""

from __future__ import annotations

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from smart_home.application.dto import UserId
from smart_home.application.ports.services import SessionTokenIssuer

bearer_scheme = HTTPBearer(auto_error=False)

UNAUTHORIZED = "Требуется авторизация."
CREDENTIALS_HEADERS = {"WWW-Authenticate": "Bearer"}


@inject
def get_current_user_id(
    tokens: FromDishka[SessionTokenIssuer],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserId:
    """Resolve the account the request was authorized as.

    Args:
        tokens: Issuer of the session tokens.
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
    user_id = tokens.resolve(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=UNAUTHORIZED,
            headers=CREDENTIALS_HEADERS,
        )
    return user_id


CurrentUserId = Annotated[UserId, Depends(get_current_user_id)]
"""Account the request was authorized as."""
