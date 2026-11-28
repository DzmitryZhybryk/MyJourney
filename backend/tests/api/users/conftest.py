"""
Users-данные для generic api-проводки (``tests/api/conftest.py``).

``event_publisher_dependency`` обязателен в overrides: боевой читает ``request.app.registry``, а
``api_app`` поднят без компонентов.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.shared.events.dependency import event_publisher_dependency
from app.users.presentation.dependencies import user_uow_dependency
from app.users.presentation.routes import users_router
from tests.fakes import FakeEventPublisher, FakeUserUnitOfWork


@pytest.fixture
def router() -> APIRouter:
    wrapper = APIRouter()
    wrapper.include_router(users_router, prefix="/users")
    return wrapper


@pytest.fixture
def router_prefix() -> str:
    return "/v1"


@pytest.fixture
def dependency_overrides(
    fake_user_uow: FakeUserUnitOfWork,
    fake_event_publisher: FakeEventPublisher,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {
        user_uow_dependency: lambda: fake_user_uow,
        event_publisher_dependency: lambda: fake_event_publisher,
    }
