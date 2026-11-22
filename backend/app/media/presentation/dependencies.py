from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.application.services.media_config import MediaConfigService
from app.media.infra.uow import MediaUnitOfWork
from app.shared.infra.db.postgres.dependency import db_session_dependency


def media_uow_dependency(
    session: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> MediaUnitOfWork:
    return MediaUnitOfWork(session)


def media_config_service_dependency(
    uow: Annotated[MediaUnitOfWork, Depends(media_uow_dependency)],
) -> MediaConfigService:
    return MediaConfigService(uow)
