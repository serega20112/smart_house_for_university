"""Сверка таблицы отказов со словарями слоёв.

Таблица в презентации — единственное место, где сбой получает код ответа. Пока
это так, каждый новый класс отказа обязан появиться в ней: тест обходит наследников
и падает, если кто-то добавил исключение и забыл про ответ интерфейса.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import status

from backend.application import errors
from backend.domain import exceptions as domain_errors
from backend.domain.identifiers import UserId
from backend.presentation.errors import (
    APPLICATION_STATUSES,
    DOMAIN_STATUSES,
    describe,
)
from backend.presentation.messages import STATE_CHANGED

DOMAIN_PACKAGE = Path(__file__).resolve().parents[3] / "src" / "backend" / "domain"
FORBIDDEN_BUILTIN_RAISES = frozenset({"ValueError", "KeyError", "TypeError", "RuntimeError"})


def subclasses_of(root: type[BaseException]) -> set[type[BaseException]]:
    """Возвращает все классы, наследующие указанному.

    Args:
        root: Корень обхода.

    Returns:
        set[type[BaseException]]: Все наследники, кроме самого корня.
    """
    found: set[type[BaseException]] = set()
    pending = list(root.__subclasses__())
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        pending.extend(current.__subclasses__())
    return found


def raised_builtin_names(tree: ast.AST) -> list[str]:
    """Возвращает имена встроенных исключений, которые модуль бросает.

    Args:
        tree: Разобранное дерево модуля.

    Returns:
        list[str]: Имена `raise`-выражений из запрещённого списка.
    """
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(target, ast.Name) and target.id in FORBIDDEN_BUILTIN_RAISES:
            names.append(target.id)
        if isinstance(target, ast.Attribute) and target.attr in FORBIDDEN_BUILTIN_RAISES:
            names.append(target.attr)
    return names


def test_every_application_error_has_a_decision() -> None:
    missing = sorted(
        error.__name__
        for error in subclasses_of(errors.ApplicationError)
        if error not in APPLICATION_STATUSES
    )
    assert missing == []


def test_every_domain_error_has_a_decision() -> None:
    missing = sorted(
        error.__name__
        for error in subclasses_of(domain_errors.DomainError)
        if error not in DOMAIN_STATUSES
    )
    assert missing == []


def test_concurrent_modification_conflicts_with_client() -> None:
    error = errors.ConcurrentModificationError("device", "abc")

    assert describe(error) == (status.HTTP_409_CONFLICT, STATE_CHANGED)


def test_deleted_account_does_not_look_like_server_failure() -> None:
    code, _ = describe(errors.AccountNotFoundError(UserId.generate()))

    assert code == status.HTTP_401_UNAUTHORIZED


def test_invalid_scenario_target_is_input_error() -> None:
    error = domain_errors.InvalidScenarioTargetError(500, 120)

    assert describe(error)[0] == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_board_with_devices_is_refused_with_their_names() -> None:
    error = errors.BoardHasDevicesError(("Лампа", "Обогреватель"))

    code, message = describe(error)

    assert code == status.HTTP_409_CONFLICT
    assert "Лампа" in message
    assert "Обогреватель" in message


@pytest.mark.parametrize(
    "module_path", sorted(DOMAIN_PACKAGE.rglob("*.py")), ids=lambda path: path.name
)
def test_domain_does_not_raise_builtin_exceptions(module_path: Path) -> None:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    assert raised_builtin_names(tree) == []
