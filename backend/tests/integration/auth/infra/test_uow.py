"""
Интеграционные тесты сборки ``AuthUnitOfWork`` против реального Postgres.

Транзакционная модель проверена в ``tests/integration/shared/infra/postgres/test_uow.py``;
здесь — то, что репозитории UoW работают на его сессии, и порядок вставок по FK внутри одной
транзакции.
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
        uow = AuthUnitOfWork(session=session)
        async with uow.transaction():
            await uow.user_credentials_repository.insert_user_credentials(
                user_credentials_entity=user_credentials_entity
            )
            await uow.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(session=reader).find_user_credentials_by_user_id(user_id=user_id)

    assert found is not None
    assert found.user_id == user_id


async def test_transaction_flush_orders_credentials_before_dependent_refresh_token(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """
    Явный ``flush()`` после родителя пускает зависимый ``refresh_token`` в ту же tx без FK-ошибки.

    Регресс на ordering вставок: ``register`` кладёт обе записи в одну транзакцию, где
    ``refresh_tokens.user_id`` → ``user_credentials.user_id`` (FK). Порядок INSERT'ов
    между разными мапперами в одном flush SQLAlchemy не гарантирует — без вмешательства
    ``INSERT refresh_tokens`` мог уйти первым и поймать ``ForeignKeyViolation``. Фикс —
    явный ``uow.flush()`` после вставки родителя: его INSERT материализуется в БД до
    зависимой строки. Воспроизводится только на реальном Postgres с FK-констрейнтом —
    фейки и раздельный сид это не покрывают.
    """
    user_id = uuid4()
    user_credentials_entity = make_user_credentials(
        user_id=user_id, email="uow-fk-order@example.com", username="uow_fk_order"
    )
    refresh_token_entity = make_refresh_token(user_id=user_id, token_hash="uow-fk-order-refresh_token_entity-hash")
    async with session_factory() as session:
        uow = AuthUnitOfWork(session=session)
        async with uow.transaction():
            await uow.user_credentials_repository.insert_user_credentials(
                user_credentials_entity=user_credentials_entity
            )
            await uow.flush()  # родитель уходит в БД до зависимого refresh_token
            await uow.refresh_token_repository.insert_refresh_token(refresh_token_entity=refresh_token_entity)
            await uow.commit()

    async with session_factory() as reader:
        found_credentials = await UserCredentialsRepository(session=reader).find_user_credentials_by_user_id(
            user_id=user_id,
        )
        found_token = await RefreshTokenRepository(session=reader).find_refresh_token_by_hash_for_update(
            token_hash="uow-fk-order-refresh_token_entity-hash",
        )

    assert found_credentials is not None
    assert found_token is not None
    assert found_token.user_id == user_id
