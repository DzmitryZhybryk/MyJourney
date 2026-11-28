"""Транзакционную модель проверяет ``integration/shared/infra/db/postgres/test_uow.py``; здесь — проводка UoW."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.users.infra.repositories import UserRepository
from app.users.infra.uow import UserUnitOfWork
from tests.builders import make_user_entity


async def test_user_repository_write_is_persisted_by_uow_commit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Запись через ``uow.user_repository`` фиксирует ``uow.commit()`` — она видна из новой сессии."""
    user_entity = make_user_entity()
    async with session_factory() as session:
        uow = UserUnitOfWork(session)
        async with uow.transaction():
            await uow.user_repository.insert_user(user_entity)
            await uow.commit()

    async with session_factory() as reader:
        found = await UserRepository(reader).find_user_by_id(user_entity.user_id)

    assert found is not None
