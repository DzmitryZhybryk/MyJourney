"""
Health-данные для generic api-проводки (``tests/api/conftest.py``).

Операционный роутер без зависимостей и без версионного префикса — три data-фикстуры вырождены:
роутер health, пустой префикс (``/healthz/`` монтируется в корень), пустая карта override'ов.
Механизм сборки ``app``/``client`` живёт в родительском ``tests/api/conftest.py``.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.health.presentation.routes import health_router


@pytest.fixture
def router() -> APIRouter:
    return health_router


@pytest.fixture
def router_prefix() -> str:
    return ""


@pytest.fixture
def dependency_overrides() -> dict[Callable[..., Any], Callable[..., Any]]:
    return {}
