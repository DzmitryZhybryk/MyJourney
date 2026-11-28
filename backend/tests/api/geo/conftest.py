from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.geo.presentation.dependencies import geo_uow_dependency
from app.geo.presentation.routes import geo_router
from tests.fakes import FakeGeoUnitOfWork


@pytest.fixture
def router() -> APIRouter:
    wrapper = APIRouter()
    wrapper.include_router(geo_router, prefix="/geo")
    return wrapper


@pytest.fixture
def router_prefix() -> str:
    return "/v1"


@pytest.fixture
def dependency_overrides(
    fake_geo_uow: FakeGeoUnitOfWork,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {geo_uow_dependency: lambda: fake_geo_uow}
