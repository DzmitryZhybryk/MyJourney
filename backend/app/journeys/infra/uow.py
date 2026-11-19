from sqlalchemy.ext.asyncio import AsyncSession

from app.journeys.application.ports.journey_repository import JourneyRepositoryPort
from app.journeys.application.ports.unit_of_work import JourneyUnitOfWorkPort
from app.journeys.infra.repositories import JourneyRepository
from app.shared.infra.postgres.uow import BaseUnitOfWork


class JourneyUnitOfWork(BaseUnitOfWork, JourneyUnitOfWorkPort):
    journey_repository: JourneyRepositoryPort

    def __init__(self, session: AsyncSession):
        super().__init__(session=session)
        self.journey_repository = JourneyRepository(session=session)
