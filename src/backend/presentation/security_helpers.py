"""Разрешение текущего аккаунта из запроса.

Авторизация выводится из токена сессии и больше ниоткуда. Идентификатор аккаунта,
пришедший в теле или в строке запроса, не читается никогда, поэтому подмена его
меняет лишь аргумент, на который сервер всё равно не смотрит.
"""

from __future__ import annotations

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.application.interface.services.session_token_issuer import SessionTokenIssuer
from backend.domain.identifiers import UserId
from backend.presentation.messages import UNAUTHORIZED

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_HEADERS = {"WWW-Authenticate": "Bearer"}


@inject
def get_current_user_id(
    tokens: FromDishka[SessionTokenIssuer],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserId:
    """Возвращает аккаунт, под которым разрешён этот запрос.

    Args:
        tokens: Выдающий токены сессии адаптер.
        credentials: Bearer-токен, который принёс клиент.

    Returns:
        UserId: Владелец, на который токен был выдан.

    Raises:
        HTTPException: Когда токена нет, он незнаком или срок его вышел.
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
"""Аккаунт, под которым разрешён запрос."""
