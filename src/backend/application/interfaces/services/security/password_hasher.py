"""Превращение пароля в хранимую форму и сравнение."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Хэширует пароль и проверяет его с хранимой формой."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Самоописываемая хранимая форма с солью и стоимостью."""

    @abstractmethod
    def verify(self, password: str, stored: str) -> bool:
        """Совпадает ли введённый пароль с хранимым."""
