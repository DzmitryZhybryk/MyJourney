"""Транзакционную модель проверяет ``integration/shared/infra/db/postgres/test_uow.py``; здесь — проводка UoW."""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.media.infra.models import MediaConfigVersion
from app.media.infra.uow import MediaUnitOfWork
from tests.builders import make_media_config_snapshot

_COUNT_CONFIG_VERSIONS = sa.select(sa.func.count()).select_from(MediaConfigVersion)


async def test_media_config_repository_write_is_persisted_by_uow_commit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Запись через ``uow.media_config_repository`` фиксирует ``uow.commit()`` — она видна из новой сессии."""
    async with session_factory() as session:
        uow = MediaUnitOfWork(session)
        async with uow.transaction():
            await uow.media_config_repository.insert_media_config(
                version=1, snapshot=make_media_config_snapshot(), created_by=None
            )
            await uow.commit()

    async with session_factory() as reader:
        count = (await reader.execute(_COUNT_CONFIG_VERSIONS)).scalar_one()

    assert count == 1
