"""Фикстуры unit-тестов исключений приложения."""

import importlib
from collections.abc import Callable
from pathlib import Path

import pytest
from starlette.requests import Request

import app
from app.shared.exceptions import AppError


def _qualified_name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


@pytest.fixture(scope="module")
def app_error_tree(module_name_of: Callable[[Path], str]) -> tuple[type[AppError], ...]:
    """
    Все классы дерева ``AppError`` из модулей приложения, корень включительно.

    Наследники видны только среди импортированных модулей, поэтому сначала импортируется каждый
    модуль пакета ``app``. Искать только в ``exceptions``-модулях нельзя: класс, объявленный в другом
    месте, попадал бы в проверку лишь тогда, когда его успел импортировать предыдущий тест. Классы из
    тестовых модулей отброшены, чтобы чужой тестовый наследник не делал результат зависимым от
    порядка запуска.
    """
    for path in Path(app.__file__).parent.rglob("*.py"):
        importlib.import_module(module_name_of(path))

    found: set[type[AppError]] = {AppError}
    pending: list[type[AppError]] = [AppError]
    while pending:
        for subclass in pending.pop().__subclasses__():
            if subclass.__module__.startswith("app.") and subclass not in found:
                found.add(subclass)
                pending.append(subclass)

    return tuple(sorted(found, key=_qualified_name))


@pytest.fixture
def bare_request() -> Request:
    """Минимальный HTTP-запрос для прямого вызова хендлера; свой на каждый тест — хендлер пишет в его состояние."""
    return Request({"type": "http"})


@pytest.fixture(scope="module")
def app_error_leaves(app_error_tree: tuple[type[AppError], ...]) -> tuple[type[AppError], ...]:
    """Листья дерева ``AppError``: классы без наследников внутри ``app``."""
    return tuple(
        cls for cls in app_error_tree if not any(issubclass(other, cls) for other in app_error_tree if other is not cls)
    )
