from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.media.presentation.admin.routes import media_admin_router
from app.media.presentation.dependencies import media_uow_dependency
from app.media.presentation.routes import media_router
from tests.fakes import FakeMediaUnitOfWork


@pytest.fixture
def router() -> APIRouter:
    wrapper = APIRouter()
    wrapper.include_router(media_router, prefix="/media")
    wrapper.include_router(media_admin_router, prefix="/admin/media")
    return wrapper


@pytest.fixture
def router_prefix() -> str:
    return "/v1"


@pytest.fixture
def dependency_overrides(
    fake_media_uow: FakeMediaUnitOfWork,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {media_uow_dependency: lambda: fake_media_uow}
