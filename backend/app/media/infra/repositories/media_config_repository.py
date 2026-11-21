from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.media.application.ports.media_config_repository import (
    MediaConfigRepositoryPort,
    MediaConfigSnapshot,
    StoredMediaConfig,
)
from app.media.infra.models import MediaConfigVersion
from app.shared.versioned_config.repository import BaseVersionedConfigRepository


class MediaConfigRepository(BaseVersionedConfigRepository[MediaConfigVersion], MediaConfigRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=MediaConfigVersion)

    async def find_latest_media_config(self) -> StoredMediaConfig | None:
        media_config_model = await self._find_latest_config()
        return (
            StoredMediaConfig(
                version=media_config_model.version,
                snapshot=media_config_model.config,
                created_at=media_config_model.created_at,
                created_by=media_config_model.created_by,
            )
            if media_config_model
            else None
        )

    async def insert_media_config(
        self, *, version: int, snapshot: MediaConfigSnapshot, created_by: UUID | None
    ) -> None:
        await self._insert_config(version=version, config=snapshot, created_by=created_by)
