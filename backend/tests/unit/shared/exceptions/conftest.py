"""Фикстуры unit-тестов исключений приложения."""

import importlib
from pathlib import Path

import pytest

import app
from app.shared.exceptions import AppError


def _qualified_name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


@pytest.fixture(scope="module")
def app_error_tree() -> tuple[type[AppError], ...]:
    """
    Все классы дерева ``AppError`` из модулей приложения, корень включительно.

    Наследники видны только среди импортированных модулей, поэтому сначала импортируется каждый
    модуль пакета ``app``. Искать только в ``exceptions``-модулях нельзя: класс, объявленный в другом
    месте, попадал бы в проверку лишь тогда, когда его успел импортировать предыдущий тест. Классы из
    тестовых модулей отброшены, чтобы чужой тестовый наследник не делал результат зависимым от
    порядка запуска.
    """
    package_root = Path(app.__file__).parent
    for path in package_root.rglob("*.py"):
        module_parts = path.relative_to(package_root.parent).with_suffix("").parts
        if path.stem == "__init__":
            module_parts = module_parts[:-1]

        importlib.import_module(".".join(module_parts))

    found: set[type[AppError]] = {AppError}
    pending: list[type[AppError]] = [AppError]
    while pending:
        for subclass in pending.pop().__subclasses__():
            if subclass.__module__.startswith("app.") and subclass not in found:
                found.add(subclass)
                pending.append(subclass)

    return tuple(sorted(found, key=_qualified_name))


@pytest.fixture(scope="module")
def app_error_leaves(app_error_tree: tuple[type[AppError], ...]) -> tuple[type[AppError], ...]:
    """Листья дерева ``AppError``: классы без наследников внутри ``app``."""
    return tuple(
        cls for cls in app_error_tree if not any(issubclass(other, cls) for other in app_error_tree if other is not cls)
    )
