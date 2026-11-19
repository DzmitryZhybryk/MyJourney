from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.application.services.city import CityService
from app.geo.infra.uow import GeoUnitOfWork
from app.shared.infra.postgres.dependency import db_session_dependency


def geo_uow_dependency(
    session: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> GeoUnitOfWork:
    return GeoUnitOfWork(session=session)


def city_service_dependency(
    uow: Annotated[GeoUnitOfWork, Depends(geo_uow_dependency)],
) -> CityService:
    return CityService(uow=uow)
