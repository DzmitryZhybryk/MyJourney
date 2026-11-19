"""
Интеграционный тест сборки ``GeoUnitOfWork`` против реального Postgres.

Транзакционная модель проверена в ``tests/integration/shared/infra/postgres/test_uow.py``;
здесь — только то, что репозиторий UoW работает на его сессии.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.geo.infra.models import GeoCity
from app.geo.infra.uow import GeoUnitOfWork


async def test_city_repository_read_works_inside_uow_transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Чтение через ``uow.city_repository`` внутри ``transaction()`` видит город, зафиксированный другой сессией."""
    city_id = uuid4()
    async with session_factory() as writer:
        writer.add(
            GeoCity(
                id=city_id,
                external_id="GeoNames:524901",
                name_en="Moscow",
                name_ru="Москва",
                country_code="RU",
                latitude=55.75,
                longitude=37.62,
                population=10_000_000,
            )
        )
        await writer.commit()

    async with session_factory() as session:
        uow = GeoUnitOfWork(session=session)
        async with uow.transaction():
            cities = await uow.city_repository.find_cities_by_ids(city_ids=(city_id,))

    assert [city_entity.city_id for city_entity in cities] == [city_id]
