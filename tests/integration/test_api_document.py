"""Сверка документа API с тем, что приложение действительно публикует.

Документ — часть контракта: по нему строят клиента и считают публичную
поверхность сервиса. Поэтому список маршрутов берётся не из головы автора
документа, а из спеки самого приложения, и расхождение в любую сторону — это
упавший тест, а не открытие, сделанное через полгода.
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.composition.app import build_api_app
from backend.config.settings import Settings

DOCUMENT = Path(__file__).resolve().parents[2] / "docs" / "api" / "api.md"

ROW = re.compile(r"^\|\s*(GET|POST|PATCH|PUT|DELETE)\s*\|\s*`([^`]+)`\s*\|", re.MULTILINE)

TOKEN_ROW = re.compile(
    r"^\|\s*(GET|POST|PATCH|PUT|DELETE)\s*\|\s*`([^`]+)`\s*\|[^|]*\|\s*(да|нет)\s*\|",
    re.MULTILINE,
)

PARAMETER = re.compile(r"\{[^}]*\}")

AUTH_SECTION = "## Авторизация"

PUBLIC_ROUTES = frozenset(
    {
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/health"),
        ("GET", "/api/ready"),
        ("GET", "/api/metrics"),
    }
)


def without_parameter_names(method: str, path: str) -> tuple[str, str]:
    """Обезличивает имена параметров пути.

    Документ называет параметр `{id}` там, где спека зовёт его `{device_id}`:
    читателю важно, что это путь к одному объекту, а не как называется поле.

    Args:
        method: Метод HTTP.
        path: Путь маршрута.

    Returns:
        tuple[str, str]: Пара «метод, путь» с пустыми скобками вместо имён.
    """
    return method.upper(), PARAMETER.sub("{}", path)


def documented_routes() -> set[tuple[str, str]]:
    """Возвращает маршруты, перечисленные таблицами документа.

    Returns:
        set[tuple[str, str]]: Пары «метод, путь» из таблиц `docs/api/api.md`.
    """
    rows = ROW.findall(DOCUMENT.read_text(encoding="utf-8"))
    assert rows, "в документе нет ни одной строки таблицы маршрутов"
    return {without_parameter_names(method, path) for method, path in rows}


def published_routes() -> set[tuple[str, str]]:
    """Возвращает маршруты, которые публикует приложение.

    Returns:
        set[tuple[str, str]]: Пары «метод, путь» из спеки приложения без
        служебных адресов самой документации.
    """
    schema = build_api_app(Settings()).openapi()
    return {
        without_parameter_names(method, path)
        for path, operations in schema["paths"].items()
        for method in operations
        if path.startswith("/api")
    }


def auth_section() -> str:
    """Возвращает текст раздела документа об авторизации.

    Returns:
        str: Раздел от заголовка до следующего заголовка второго уровня.
    """
    text = DOCUMENT.read_text(encoding="utf-8")
    assert AUTH_SECTION in text, "в документе нет раздела об авторизации"
    return text.split(AUTH_SECTION, 1)[1].split("\n## ", 1)[0]


def test_document_lists_every_published_route() -> None:
    """Не даёт документу и приложению разойтись в списке маршрутов."""
    documented = documented_routes()
    published = published_routes()

    assert published - documented == set(), "маршруты есть в приложении, но не в документе"
    assert documented - published == set(), "маршруты описаны в документе, но их нет"


def test_auth_table_marks_every_route_with_its_token_requirement() -> None:
    """Держит поверхность без токена равной тому, что названо в таблице авторизации.

    Таблица авторизации — единственное место, по которому читатель решает, где
    нужен токен, а где нет. Поэтому у каждой её строки есть признак, и множество
    ручек без токена обязано совпасть с тем, что сервис действительно открывает.
    """
    section = auth_section()
    marks = TOKEN_ROW.findall(section)

    assert marks, "в таблице авторизации нет ни одной строки с признаком токена"
    assert len(marks) == len(ROW.findall(section)), "у каждой строки нужен признак токена"
    assert {(method.upper(), path) for method, path, token in marks if token == "нет"} == set(
        PUBLIC_ROUTES
    )
