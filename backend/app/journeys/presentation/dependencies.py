from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.application.services.city import CityService
from app.geo.presentation.dependencies import city_service_dependency
from app.journeys.application.services.journey import JourneyService
from app.journeys.infra.clients.internal_cities_client import InternalCitiesClient
from app.journeys.infra.uow import JourneyUnitOfWork
from app.shared.infra.postgres.dependency import db_session_dependency


def journey_uow_dependency(
    session: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> JourneyUnitOfWork:
    return JourneyUnitOfWork(session=session)


def cities_client_dependency(
    city_service: Annotated[CityService, Depends(city_service_dependency)],
) -> InternalCitiesClient:
    return InternalCitiesClient(city_service=city_service)


def journey_service_dependency(
    *,
    uow: Annotated[JourneyUnitOfWork, Depends(journey_uow_dependency)],
    cities_client: Annotated[InternalCitiesClient, Depends(cities_client_dependency)],
) -> JourneyService:
    return JourneyService(uow=uow, cities_client=cities_client)
