"""Health — операционный роутер вне ``/v1`` и без зависимостей: префикс пустой, подменять нечего."""

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
