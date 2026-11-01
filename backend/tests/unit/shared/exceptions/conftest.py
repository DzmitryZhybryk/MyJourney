"""Фикстуры unit-тестов исключений приложения."""

import importlib
from pathlib import Path

import pytest

import app
from app.shared.exceptions import AppError


@pytest.fixture
def app_error_leaves() -> tuple[type[AppError], ...]:
    """
    Листья дерева ``AppError`` из модулей приложения: классы без наследников внутри ``app``.

    Наследники видны только среди импортированных модулей, поэтому сначала импортируется каждый
    модуль ``exceptions.py`` и каждый модуль пакетов ``exceptions/``. Классы из тестовых модулей
    отброшены, чтобы чужой тестовый наследник не делал результат зависимым от порядка запуска.
    """
    package_root = Path(app.__file__).parent
    for path in package_root.rglob("*.py"):
        module_parts = path.relative_to(package_root.parent).with_suffix("").parts
        if path.stem == "__init__":
            module_parts = module_parts[:-1]

        if "exceptions" in module_parts:
            importlib.import_module(".".join(module_parts))

    found: set[type[AppError]] = set()
    pending: list[type[AppError]] = [AppError]
    while pending:
        for subclass in pending.pop().__subclasses__():
            if subclass.__module__.startswith("app.") and subclass not in found:
                found.add(subclass)
                pending.append(subclass)

    leaves = (cls for cls in found if not any(issubclass(other, cls) for other in found - {cls}))
    return tuple(sorted(leaves, key=lambda cls: f"{cls.__module__}.{cls.__qualname__}"))
