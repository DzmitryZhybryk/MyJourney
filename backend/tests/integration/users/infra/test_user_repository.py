import datetime as dt
from typing import Final
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.infra.db.postgres.exceptions import StaleRowVersionError
from app.users.infra.models import User
from app.users.infra.repositories import UserRepository
from tests.builders import make_user_entity

_TERMS_ACCEPTED_AT: Final[dt.datetime] = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
_UPDATED_AT: Final[dt.datetime] = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
_DELETED_AT: Final[dt.datetime] = dt.datetime(2026, 1, 3, tzinfo=dt.UTC)


async def test_insert_then_find_user_by_id_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Insert и commit → поиск по id отдаёт сущность со всеми полями профиля."""
    user_entity = make_user_entity(
        display_name="Alice D.",
        terms_accepted_at=_TERMS_ACCEPTED_AT,
        marketing_emails_consent=True,
        updated_at=_UPDATED_AT,
    )
    async with session_factory() as writer:
        await UserRepository(writer).insert_user(user_entity)
        await writer.commit()

    async with session_factory() as reader:
        found = await UserRepository(reader).find_user_by_id(user_entity.user_id)

    assert found is not None
    assert found.user_id == user_entity.user_id
    assert found.display_name == "Alice D."
    assert found.terms_accepted_at == _TERMS_ACCEPTED_AT
    assert found.marketing_emails_consent is True
    assert found.created_at == user_entity.created_at
    assert found.updated_at == _UPDATED_AT
    assert found.deleted_at is None


async def test_find_user_by_id_returns_soft_deleted_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Soft-deleted запись не фильтруется: репозиторий отдаёт её с ``deleted_at``."""
    user_entity = make_user_entity(deleted_at=_DELETED_AT)
    async with session_factory() as writer:
        await UserRepository(writer).insert_user(user_entity)
        await writer.commit()

    async with session_factory() as reader:
        found = await UserRepository(reader).find_user_by_id(user_entity.user_id)

    assert found is not None
    assert found.deleted_at == _DELETED_AT
    assert found.is_deleted is True


async def test_find_user_by_id_unknown_id_returns_none(db_session: AsyncSession) -> None:
    """Неизвестный id → ``None``."""
    found = await UserRepository(db_session).find_user_by_id(uuid4())

    assert found is None


async def test_find_user_by_id_for_update_locks_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Row-лок реальный: вторая сессия не возьмёт строку под ``NOWAIT``."""
    user_entity = make_user_entity()
    async with session_factory() as writer:
        await UserRepository(writer).insert_user(user_entity)
        await writer.commit()

    async with session_factory() as holder, session_factory() as contender:
        locked = await UserRepository(holder).find_user_by_id_for_update(user_entity.user_id)
        assert locked is not None

        nowait_query = sa.select(User).where(User.id == user_entity.user_id).with_for_update(nowait=True)
        with pytest.raises(OperationalError):
            await contender.execute(nowait_query)


async def test_find_user_by_id_for_update_returns_soft_deleted_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Под локом soft-deleted запись тоже не фильтруется."""
    user_entity = make_user_entity(deleted_at=_DELETED_AT)
    async with session_factory() as writer:
        await UserRepository(writer).insert_user(user_entity)
        await writer.commit()

    async with session_factory() as reader:
        found = await UserRepository(reader).find_user_by_id_for_update(user_entity.user_id)

    assert found is not None
    assert found.deleted_at == _DELETED_AT


async def test_find_user_by_id_for_update_unknown_id_returns_none(db_session: AsyncSession) -> None:
    """Неизвестный id под локом → ``None``."""
    found = await UserRepository(db_session).find_user_by_id_for_update(uuid4())

    assert found is None


async def test_update_user_by_id_persists_profile_changes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Изменённые поля и ``updated_at`` записаны; ``created_at`` и дата принятия условий прежние."""
    user_entity = make_user_entity(
        display_name="alice",
        marketing_emails_consent=True,
        terms_accepted_at=_TERMS_ACCEPTED_AT,
        updated_at=_UPDATED_AT,
    )
    async with session_factory() as writer:
        await UserRepository(writer).insert_user(user_entity)
        await writer.commit()

    async with session_factory() as editor:
        repository = UserRepository(editor)
        editable = await repository.find_user_by_id_for_update(user_entity.user_id)
        assert editable is not None
        editable.update_profile(display_name="Alice D.", marketing_emails_consent=False)
        await repository.update_user_by_id(editable)
        await editor.commit()

    async with session_factory() as reader:
        found = await UserRepository(reader).find_user_by_id(user_entity.user_id)

    assert found is not None
    assert found.display_name == "Alice D."
    assert found.marketing_emails_consent is False
    assert found.updated_at == editable.updated_at
    assert found.updated_at != _UPDATED_AT
    assert found.created_at == user_entity.created_at
    assert found.terms_accepted_at == _TERMS_ACCEPTED_AT


async def test_update_user_by_id_entity_changed_twice_raises_stale(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Сущность изменена дважды после чтения → ``StaleRowVersionError``, в базе прежнее имя и версия."""
    user_entity = make_user_entity(display_name="alice")
    async with session_factory() as writer:
        await UserRepository(writer).insert_user(user_entity)
        await writer.commit()

    user_entity.update_profile(display_name="Alice D.")
    user_entity.update_profile(display_name="Alice Doe")
    async with session_factory() as editor:
        with pytest.raises(StaleRowVersionError):
            await UserRepository(editor).update_user_by_id(user_entity)

    async with session_factory() as reader:
        found = await UserRepository(reader).find_user_by_id(user_entity.user_id)

    assert found is not None
    assert found.display_name == "alice"
    assert found.version == 1


async def test_update_user_by_id_leaves_other_users_untouched(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """UPDATE идёт только по PK: соседний пользователь не меняется."""
    target = make_user_entity(display_name="alice")
    neighbour = make_user_entity(display_name="bob")
    async with session_factory() as writer:
        repository = UserRepository(writer)
        await repository.insert_user(target)
        await repository.insert_user(neighbour)
        await writer.commit()

    target.update_profile(display_name="Alice D.")
    async with session_factory() as editor:
        await UserRepository(editor).update_user_by_id(target)
        await editor.commit()

    async with session_factory() as reader:
        found = await UserRepository(reader).find_user_by_id(neighbour.user_id)

    assert found is not None
    assert found.display_name == "bob"
