"""
Users-данные для generic api-проводки (``tests/api/conftest.py``).

Три data-фикстуры, которыми generic-фикстура ``app`` собирает приложение: ``router``
(users-роутер), ``router_prefix`` (``/v1/users``) и ``dependency_overrides``. Подменяется
``user_service_dependency`` (у users цепочка dependencies свёрнута в один провайдер),
но сервис внутри настоящий — фейковая только I/O-граница (``FakeUserUnitOfWork`` поверх
``fake_user_repository`` из корневого conftest). ``current_user_id_dependency`` остаётся
реальным: Bearer декодится settings-секретом через ``mint_access_token``.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.users.application.services.user import UserService
from app.users.presentation.dependencies import user_service_dependency
from app.users.presentation.routes import users_router
from tests.fakes import FakeUserUnitOfWork

_USERS_ROUTER_PREFIX = "/v1/users"


@pytest.fixture
def router() -> APIRouter:
    return users_router


@pytest.fixture
def router_prefix() -> str:
    return _USERS_ROUTER_PREFIX


@pytest.fixture
def dependency_overrides(
    fake_user_uow: FakeUserUnitOfWork,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {user_service_dependency: lambda: UserService(uow=fake_user_uow)}
