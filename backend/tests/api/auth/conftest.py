"""
Auth-данные для generic api-проводки (``tests/api/conftest.py``).

Здесь только то, чьё определение **импортирует auth**: три data-фикстуры, которыми
generic-фикстура ``app`` собирает приложение — ``router`` (auth-роутер), ``router_prefix``
(``/v1/auth``) и ``dependency_overrides`` (какие листовые auth-deps чем подменить). Сам
механизм сборки ``app``, ``client``, фейки shared-инфры (salted/deterministic hasher,
task-bus) и ``mint_access_token`` живут в родительском ``tests/api/conftest.py``; фейки
I/O-границы (UoW, users-client, email-настройки) — в корневом ``tests/conftest.py``.

Подменяем лишь **листовые** dependency — UoW, users-client, salted-hasher, task-bus,
email-настройки. Реальными остаются ``auth_service``/``email_verification_service``/
``token_issuer``/``current_user_id`` (они эти листья и компонуют) — так тест прогоняет
настоящую проводку сервисов, выпуск/декод JWT, куки и exception-handler'ы, фейкая только
ввод-вывод. ``task_bus_dependency`` обязателен в overrides: боевой читает
``request.app.registry.get(ProcrastinateTaskBus)``, а ``api_app`` поднят без компонентов —
registry пуст и боевой бы упал.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.auth.application.config import EmailVerificationConfig
from app.auth.presentation.dependencies import (
    auth_uow_dependency,
    email_verification_config_dependency,
    salted_hasher_dependency,
    task_bus_dependency,
    users_client_dependency,
)
from app.auth.presentation.routes import auth_router
from tests.fakes import (
    FakeAuthUnitOfWork,
    FakeSaltedHasher,
    FakeTaskBus,
    FakeUsersClient,
)

_AUTH_ROUTER_PREFIX = "/v1/auth"


@pytest.fixture
def router() -> APIRouter:
    return auth_router


@pytest.fixture
def router_prefix() -> str:
    return _AUTH_ROUTER_PREFIX


@pytest.fixture
def dependency_overrides(
    fake_uow: FakeAuthUnitOfWork,
    fake_users_client: FakeUsersClient,
    fake_salted_hasher: FakeSaltedHasher,
    fake_task_bus: FakeTaskBus,
    email_verification_config: EmailVerificationConfig,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {
        auth_uow_dependency: lambda: fake_uow,
        users_client_dependency: lambda: fake_users_client,
        salted_hasher_dependency: lambda: fake_salted_hasher,
        task_bus_dependency: lambda: fake_task_bus,
        email_verification_config_dependency: lambda: email_verification_config,
    }
