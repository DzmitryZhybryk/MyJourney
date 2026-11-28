import datetime as dt
from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.infra.models import RefreshToken
from app.auth.infra.repositories import RefreshTokenRepository
from tests.builders import make_refresh_token

_EXPIRES_AT = dt.datetime(2030, 1, 1, tzinfo=dt.UTC)
_REVOKED_AT = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
_ALREADY_REVOKED_AT = dt.datetime(2020, 1, 1, tzinfo=dt.UTC)


async def test_insert_then_find_refresh_token_by_hash_for_update_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """Insert и commit → поиск по hash из новой сессии отдаёт ту же сущность."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="rt-roundtrip@example.com", username="rt_roundtrip")
    refresh_token_entity = make_refresh_token(user_id=user_id, token_hash="roundtrip-hash", expires_at=_EXPIRES_AT)
    async with session_factory() as writer:
        await RefreshTokenRepository(writer).insert_refresh_token(refresh_token_entity)
        await writer.commit()

    async with session_factory() as reader:
        found = await RefreshTokenRepository(reader).find_refresh_token_by_hash_for_update(
            "roundtrip-hash",
        )

    assert found is not None
    assert found.token_id == refresh_token_entity.token_id
    assert found.user_id == user_id
    assert found.token_hash == "roundtrip-hash"
    assert found.expires_at == _EXPIRES_AT
    assert found.revoked_at is None


async def test_find_refresh_token_by_hash_for_update_unknown_hash_returns_none(db_session: AsyncSession) -> None:
    """Поиск по несуществующему hash'у возвращает ``None``, а не падает."""
    found = await RefreshTokenRepository(db_session).find_refresh_token_by_hash_for_update(
        "missing-hash",
    )

    assert found is None


async def test_update_refresh_token_by_id_persists_revoked_at(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """Изменённый ``revoked_at`` виден из новой сессии."""
    user_id = uuid4()
    token_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="rt-update@example.com", username="rt_update")
    refresh_token_entity = make_refresh_token(
        token_id=token_id, user_id=user_id, token_hash="update-hash", expires_at=_EXPIRES_AT
    )
    async with session_factory() as writer:
        await RefreshTokenRepository(writer).insert_refresh_token(refresh_token_entity)
        await writer.commit()

    revoked_token = make_refresh_token(
        token_id=token_id,
        user_id=user_id,
        token_hash="update-hash",
        expires_at=_EXPIRES_AT,
        revoked_at=_REVOKED_AT,
    )
    async with session_factory() as writer:
        await RefreshTokenRepository(writer).update_refresh_token_by_id(revoked_token)
        await writer.commit()

    async with session_factory() as reader:
        found = await RefreshTokenRepository(reader).find_refresh_token_by_hash_for_update(
            "update-hash",
        )

    assert found is not None
    assert found.revoked_at == _REVOKED_AT


async def test_revoke_all_active_refresh_tokens_by_user_id_revokes_only_active(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """Отзываются только активные токены; уже отозванный не перезаписывается."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="rt-revoke@example.com", username="rt_revoke")
    active_one = make_refresh_token(user_id=user_id, token_hash="active-1", expires_at=_EXPIRES_AT)
    active_two = make_refresh_token(user_id=user_id, token_hash="active-2", expires_at=_EXPIRES_AT)
    already_revoked = make_refresh_token(
        user_id=user_id,
        token_hash="revoked-1",
        expires_at=_EXPIRES_AT,
        revoked_at=_ALREADY_REVOKED_AT,
    )
    async with session_factory() as writer:
        repository = RefreshTokenRepository(writer)
        for refresh_token_entity in (active_one, active_two, already_revoked):
            await repository.insert_refresh_token(refresh_token_entity)

        await writer.commit()

    async with session_factory() as actor:
        await RefreshTokenRepository(actor).revoke_all_active_refresh_tokens_by_user_id(user_id)
        await actor.commit()

    async with session_factory() as reader:
        repository = RefreshTokenRepository(reader)
        found_active_one = await repository.find_refresh_token_by_hash_for_update("active-1")
        found_active_two = await repository.find_refresh_token_by_hash_for_update("active-2")
        found_already_revoked = await repository.find_refresh_token_by_hash_for_update("revoked-1")

    assert found_active_one is not None
    assert found_active_one.revoked_at is not None
    assert found_active_two is not None
    assert found_active_two.revoked_at is not None
    assert found_already_revoked is not None
    assert found_already_revoked.revoked_at == _ALREADY_REVOKED_AT


async def test_find_refresh_token_by_hash_for_update_locks_row(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """Row-лок реальный: вторая сессия не возьмёт строку под ``NOWAIT``."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="rt-lock@example.com", username="rt_lock")
    refresh_token_entity = make_refresh_token(user_id=user_id, token_hash="lock-hash", expires_at=_EXPIRES_AT)
    async with session_factory() as writer:
        await RefreshTokenRepository(writer).insert_refresh_token(refresh_token_entity)
        await writer.commit()

    async with session_factory() as holder, session_factory() as contender:
        # holder берёт row-лок через FOR UPDATE и держит транзакцию открытой
        locked = await RefreshTokenRepository(holder).find_refresh_token_by_hash_for_update(
            "lock-hash",
        )
        assert locked is not None

        # тот же row под NOWAIT второй сессии недоступен → LockNotAvailable
        nowait_query = (
            sa.select(RefreshToken).where(RefreshToken.token_hash == "lock-hash").with_for_update(nowait=True)
        )
        with pytest.raises(OperationalError):
            await contender.execute(nowait_query)
