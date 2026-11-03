"""
Интеграционный тест сборки ``JourneyUnitOfWork`` против реального Postgres.

Транзакционная модель проверена в ``tests/integration/shared/infra/postgres/test_uow.py``;
здесь — только то, что репозиторий UoW работает на его сессии.
"""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.journeys.infra.models import Journey
from app.journeys.infra.uow import JourneyUnitOfWork
from tests.builders import make_journey

_COUNT_JOURNEYS = sa.select(sa.func.count()).select_from(Journey)


async def test_journey_repository_write_is_persisted_by_uow_commit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Запись через ``uow.journey_repository`` фиксирует ``uow.commit()`` — она видна из новой сессии."""
    journey_entity = make_journey()
    async with session_factory() as session:
        uow = JourneyUnitOfWork(session=session)
        async with uow.transaction():
            await uow.journey_repository.insert_journey(journey_entity=journey_entity)
            await uow.commit()

    async with session_factory() as reader:
        count = (await reader.execute(_COUNT_JOURNEYS)).scalar_one()

    assert count == 1
