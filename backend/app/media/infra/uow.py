from sqlalchemy.ext.asyncio import AsyncSession

from app.media.application.ports.media_config_repository import MediaConfigRepositoryPort
from app.media.application.ports.unit_of_work import MediaUnitOfWorkPort
from app.media.infra.repositories import MediaConfigRepository
from app.shared.infra.postgres.uow import BaseUnitOfWork


class MediaUnitOfWork(BaseUnitOfWork, MediaUnitOfWorkPort):
    media_config_repository: MediaConfigRepositoryPort

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.media_config_repository = MediaConfigRepository(session)
