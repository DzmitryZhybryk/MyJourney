"""
Journeys-данные для generic api-проводки (``tests/api/conftest.py``).

Три data-фикстуры, которыми generic-фикстура ``app`` собирает приложение: ``router``
(journey-роутер), ``router_prefix`` (``/v1/journeys``) и ``dependency_overrides``. Подменяем
только **листовую** dependency — UoW; реальными остаются ``journey_service`` и
``current_user_id_dependency`` (Bearer проходит настоящий декод реальным settings-секретом
через ``mint_access_token``). Контракт-тест ``test_transport_type_contract`` собирает app сам
и эти фикстуры не трогает.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import APIRouter

from app.journeys.presentation.dependencies import cities_client_dependency, journey_uow_dependency
from app.journeys.presentation.routes import journey_router
from tests.fakes import FakeCitiesClient, FakeJourneyUnitOfWork

_JOURNEYS_ROUTER_PREFIX = "/v1/journeys"


@pytest.fixture
def router() -> APIRouter:
    return journey_router


@pytest.fixture
def router_prefix() -> str:
    return _JOURNEYS_ROUTER_PREFIX


@pytest.fixture
def dependency_overrides(
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_cities_client: FakeCitiesClient,
) -> dict[Callable[..., Any], Callable[..., Any]]:
    return {
        journey_uow_dependency: lambda: fake_journey_uow,
        cities_client_dependency: lambda: fake_cities_client,
    }
