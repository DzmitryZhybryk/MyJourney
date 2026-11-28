from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.backoffice.presentation.admin.routes import backoffice_admin_router
from app.backoffice.presentation.dependencies import backoffice_uow_dependency
from tests.fakes import FakeBackofficeUnitOfWork


@pytest.fixture
def router() -> APIRouter:
    wrapper = APIRouter()
    wrapper.include_router(backoffice_admin_router, prefix="/admin/backoffice")
    return wrapper


@pytest.fixture
def router_prefix() -> str:
    return "/v1"


@pytest.fixture
def dependency_overrides(
    fake_backoffice_uow: FakeBackofficeUnitOfWork,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {backoffice_uow_dependency: lambda: fake_backoffice_uow}
