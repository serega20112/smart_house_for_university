"""Сверка `.env.example` с переменными, которые действительно читают настройки.

Пример окружения обещает быть полным списком того, что понимает `Settings`. Обещание
держится не глазами, а чтением кода: набор переменных берётся из вызовов `os.getenv` в
секциях конфигурации, поэтому новая настройка без строки в примере и строка в примере без
настройки одинаково роняют проверку.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SECTIONS = ROOT / "src" / "backend" / "config" / "sections"
ENV_EXAMPLE = ROOT / ".env.example"


def declared(path: Path) -> set[str]:
    """Возвращает переменные, объявленные в файле окружения.

    Args:
        path: Файл в формате `.env`.

    Returns:
        set[str]: Имена переменных без значений.
    """
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        names.add(stripped.split("=", 1)[0].strip())
    return names


def read(directory: Path) -> set[str]:
    """Возвращает переменные, которые читают загрузчики секций.

    Args:
        directory: Каталог с секциями `Settings`.

    Returns:
        set[str]: Имена переменных из вызовов `os.getenv`.
    """
    names: set[str] = set()
    for module in directory.glob("*.py"):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            called = node.func
            if not isinstance(called, ast.Attribute) or called.attr != "getenv":
                continue
            name = node.args[0]
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                names.add(name.value)
    return names


def test_env_example_declares_every_read_variable() -> None:
    """Каждая переменная, которую читает `Settings`, есть в примере.

    Returns:
        None: Только сверка полноты примера.
    """
    assert read(SECTIONS) - declared(ENV_EXAMPLE) == set()


def test_env_example_declares_nothing_unknown() -> None:
    """Пример не обещает переменных, которых никто не читает.

    Returns:
        None: Только сверка отсутствия лишних строк.
    """
    assert declared(ENV_EXAMPLE) - read(SECTIONS) == set()
