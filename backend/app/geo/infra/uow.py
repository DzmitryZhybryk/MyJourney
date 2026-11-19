from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.application.ports.city_repository import CityRepositoryPort
from app.geo.application.ports.unit_of_work import GeoUnitOfWorkPort
from app.geo.infra.repositories import CityRepository
from app.shared.infra.postgres.uow import BaseUnitOfWork


class GeoUnitOfWork(BaseUnitOfWork, GeoUnitOfWorkPort):
    city_repository: CityRepositoryPort

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.city_repository = CityRepository(session=session)
