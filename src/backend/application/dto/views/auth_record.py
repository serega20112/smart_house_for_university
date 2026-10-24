"""Учётные данные и профиль аккаунта одним чтением.

Вход в систему — это всегда и проверка пароля, и показ профиля. Раньше это было два
запроса (`get_credentials` затем `get_profile`), то есть два round-trip к хранилищу на
один логин. Здесь они собраны в один читаемый образ: проверка берёт хеш, а ответ —
профиль, и второй запрос не нужен.

Сохранённый пароль наружу не отдаётся: `profile()` отрезает его, оставляя только то,
что разрешено показать человеку.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.application.dto.views.account_profile import AccountProfile
from backend.domain.identifiers import UserId


@dataclass(frozen=True, slots=True)
class AuthRecord:
    """Пара «учётные данные + профиль» одного аккаунта.

    Attributes:
        user_id: Идентификатор аккаунта.
        email: Логин аккаунта.
        display_name: Имя, показанное в интерфейсе.
        created_at: Момент создания аккаунта.
        password_hash: Сохранённая форма пароля для сверки.
    """

    user_id: UserId
    email: str
    display_name: str
    created_at: datetime
    password_hash: str

    def profile(self) -> AccountProfile:
        """Возвращает публичную часть аккаунта, не трогая хеш пароля.

        Returns:
            AccountProfile: Профиль для ответа вошедшему человеку.
        """
        return AccountProfile(
            id=self.user_id,
            email=self.email,
            display_name=self.display_name,
            created_at=self.created_at,
        )
