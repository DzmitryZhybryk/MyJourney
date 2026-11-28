"""
Транзакционную модель проверяет ``integration/shared/infra/db/postgres/test_uow.py``; здесь — проводка UoW
и порядок вставок по FK: SQLAlchemy не упорядочивает INSERT разных мапперов внутри одного flush.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.infra.repositories import RefreshTokenRepository, UserCredentialsRepository
from app.auth.infra.uow import AuthUnitOfWork
from tests.builders import make_refresh_token, make_user_credentials


async def test_user_credentials_repository_write_is_persisted_by_uow_commit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Запись через ``uow.user_credentials_repository`` фиксирует ``uow.commit()`` — она видна из новой сессии."""
    user_id = uuid4()
    user_credentials_entity = make_user_credentials(
        user_id=user_id, email="uow-commit@example.com", username="uow_commit"
    )
    async with session_factory() as session:
        uow = AuthUnitOfWork(session)
        async with uow.transaction():
            await uow.user_credentials_repository.insert_user_credentials(user_credentials_entity)
            await uow.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(reader).find_user_credentials_by_user_id(user_id)

    assert found is not None
    assert found.user_id == user_id


async def test_transaction_flush_orders_credentials_before_dependent_refresh_token(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Явный ``flush()`` после учётки пускает зависимый refresh-токен в ту же транзакцию без FK-ошибки."""
    user_id = uuid4()
    user_credentials_entity = make_user_credentials(
        user_id=user_id, email="uow-fk-order@example.com", username="uow_fk_order"
    )
    refresh_token_entity = make_refresh_token(user_id=user_id, token_hash="uow-fk-order-refresh_token_entity-hash")
    async with session_factory() as session:
        uow = AuthUnitOfWork(session)
        async with uow.transaction():
            await uow.user_credentials_repository.insert_user_credentials(user_credentials_entity)
            await uow.flush()  # родитель уходит в БД до зависимого refresh_token
            await uow.refresh_token_repository.insert_refresh_token(refresh_token_entity)
            await uow.commit()

    async with session_factory() as reader:
        found_credentials = await UserCredentialsRepository(reader).find_user_credentials_by_user_id(
            user_id,
        )
        found_token = await RefreshTokenRepository(reader).find_refresh_token_by_hash_for_update(
            "uow-fk-order-refresh_token_entity-hash",
        )

    assert found_credentials is not None
    assert found_token is not None
    assert found_token.user_id == user_id
