"""
``task_bus_dependency`` и ``event_publisher_dependency`` обязательны в overrides: боевые читают
``request.app.registry``, а ``api_app`` поднят без компонентов.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.auth.application.config import EmailVerificationConfig
from app.auth.presentation.admin.routes import auth_admin_router
from app.auth.presentation.dependencies import (
    auth_uow_dependency,
    email_verification_config_dependency,
    salted_hasher_dependency,
    task_bus_dependency,
    users_client_dependency,
)
from app.auth.presentation.routes import auth_router
from app.shared.events.dependency import event_publisher_dependency
from tests.fakes import (
    FakeAuthUnitOfWork,
    FakeEventPublisher,
    FakeSaltedHasher,
    FakeTaskBus,
    FakeUsersClient,
)


@pytest.fixture
def router() -> APIRouter:
    wrapper = APIRouter()
    wrapper.include_router(auth_router, prefix="/auth")
    wrapper.include_router(auth_admin_router, prefix="/admin/auth")
    return wrapper


@pytest.fixture
def router_prefix() -> str:
    return "/v1"


@pytest.fixture
def dependency_overrides(
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_users_client: FakeUsersClient,
    fake_salted_hasher: FakeSaltedHasher,
    fake_task_bus: FakeTaskBus,
    fake_event_publisher: FakeEventPublisher,
    email_verification_config: EmailVerificationConfig,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {
        auth_uow_dependency: lambda: fake_auth_uow,
        users_client_dependency: lambda: fake_users_client,
        salted_hasher_dependency: lambda: fake_salted_hasher,
        task_bus_dependency: lambda: fake_task_bus,
        event_publisher_dependency: lambda: fake_event_publisher,
        email_verification_config_dependency: lambda: email_verification_config,
    }
