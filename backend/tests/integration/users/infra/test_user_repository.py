"""
Интеграционные тесты ``UserRepository`` против реального Postgres.

Покрывают round-trip entity↔БД по каждой колонке профиля и то, что soft-deleted
запись репозиторий отдаёт как есть (интерпретация удаления — забота домена).
"""

import datetime as dt
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.users.infra.repositories import UserRepository
from tests.builders import make_user_entity

_TERMS_ACCEPTED_AT = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
_UPDATED_AT = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
_DELETED_AT = dt.datetime(2026, 1, 3, tzinfo=dt.UTC)


async def test_insert_then_find_by_id_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """insert + commit → ``find_user_by_id`` возвращает сущность со всеми полями профиля."""
    user_entity = make_user_entity(
        display_name="Alice D.",
        terms_accepted_at=_TERMS_ACCEPTED_AT,
        marketing_emails_consent=True,
        updated_at=_UPDATED_AT,
    )
    async with session_factory() as writer:
        await UserRepository(session=writer).insert_user(user_entity=user_entity)
        await writer.commit()

    async with session_factory() as reader:
        found = await UserRepository(session=reader).find_user_by_id(user_id=user_entity.user_id)

    assert found is not None
    assert found.user_id == user_entity.user_id
    assert found.display_name == "Alice D."
    assert found.terms_accepted_at == _TERMS_ACCEPTED_AT
    assert found.marketing_emails_consent is True
    assert found.created_at == user_entity.created_at
    assert found.updated_at == _UPDATED_AT
    assert found.deleted_at is None


async def test_find_by_id_returns_soft_deleted_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Soft-deleted запись не фильтруется: репозиторий отдаёт её с ``deleted_at``."""
    user_entity = make_user_entity(deleted_at=_DELETED_AT)
    async with session_factory() as writer:
        await UserRepository(session=writer).insert_user(user_entity=user_entity)
        await writer.commit()

    async with session_factory() as reader:
        found = await UserRepository(session=reader).find_user_by_id(user_id=user_entity.user_id)

    assert found is not None
    assert found.deleted_at == _DELETED_AT
    assert found.is_deleted is True


async def test_find_by_unknown_id_returns_none(db_session: AsyncSession) -> None:
    """Неизвестный id → ``None``."""
    found = await UserRepository(session=db_session).find_user_by_id(user_id=uuid4())

    assert found is None
