from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.journeys.presentation.dependencies import cities_client_dependency, journey_uow_dependency
from app.journeys.presentation.routes import journey_router
from tests.fakes import FakeCitiesClient, FakeJourneyUnitOfWork


@pytest.fixture
def router() -> APIRouter:
    wrapper = APIRouter()
    wrapper.include_router(journey_router, prefix="/journeys")
    return wrapper


@pytest.fixture
def router_prefix() -> str:
    return "/v1"


@pytest.fixture
def dependency_overrides(
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_cities_client: FakeCitiesClient,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {
        journey_uow_dependency: lambda: fake_journey_uow,
        cities_client_dependency: lambda: fake_cities_client,
    }
