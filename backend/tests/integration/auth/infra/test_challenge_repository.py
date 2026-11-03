"""
Интеграционные тесты ``ChallengeRepository`` против реального Postgres.

Покрывают round-trip, фильтр «только активный» (``used_at IS NULL``), партиальный
unique-индекс (один активный challenge типа на пользователя) и реальный row-лок
``SELECT ... FOR UPDATE`` (защита от потери инкремента попыток в verify-флоу).
"""

import datetime as dt
from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.domain.enums import ChallengeTypeEnum
from app.auth.infra.models import Challenge
from app.auth.infra.repositories import ChallengeRepository
from tests.builders import make_challenge

_EXPIRES_AT = dt.datetime(2030, 1, 1, tzinfo=dt.UTC)
_LAST_SENT_AT = dt.datetime(2029, 12, 31, 23, 45, tzinfo=dt.UTC)
_USED_AT = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)


async def test_insert_then_find_active_for_update_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """insert + commit → ``find_active_challenge_for_update`` возвращает ту же сущность."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="ch-roundtrip@example.com", username="ch_roundtrip")
    challenge_entity = make_challenge(
        user_id=user_id,
        challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        code_ciphertext="roundtrip-code",
        expires_at=_EXPIRES_AT,
        last_sent_at=_LAST_SENT_AT,
    )
    async with session_factory() as writer:
        await ChallengeRepository(session=writer).insert_challenge(challenge_entity=challenge_entity)
        await writer.commit()

    async with session_factory() as reader:
        found = await ChallengeRepository(session=reader).find_active_challenge_for_update(
            user_id=user_id,
            challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        )

    assert found is not None
    assert found.challenge_id == challenge_entity.challenge_id
    assert found.user_id == user_id
    assert found.challenge_type is ChallengeTypeEnum.EMAIL_VERIFICATION
    assert found.code_ciphertext == "roundtrip-code"
    assert found.expires_at == _EXPIRES_AT
    assert found.last_sent_at == _LAST_SENT_AT
    assert found.attempts == 0


async def test_find_active_excludes_used_challenge(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """Использованный challenge (``used_at`` задан) не считается активным — выборка вернёт ``None``."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="ch-used@example.com", username="ch_used")
    used_challenge = make_challenge(
        user_id=user_id,
        challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        expires_at=_EXPIRES_AT,
        used_at=_USED_AT,
    )
    async with session_factory() as writer:
        await ChallengeRepository(session=writer).insert_challenge(challenge_entity=used_challenge)
        await writer.commit()

    async with session_factory() as reader:
        found = await ChallengeRepository(session=reader).find_active_challenge_for_update(
            user_id=user_id,
            challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        )

    assert found is None


async def test_update_challenge_persists_attempts_and_resend(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """``update_challenge_by_id`` персистит счётчик попыток и продление после повторной отправки."""
    user_id = uuid4()
    challenge_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="ch-update@example.com", username="ch_update")
    challenge_entity = make_challenge(
        challenge_id=challenge_id,
        user_id=user_id,
        challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        expires_at=_EXPIRES_AT,
        attempts=0,
    )
    async with session_factory() as writer:
        await ChallengeRepository(session=writer).insert_challenge(challenge_entity=challenge_entity)
        await writer.commit()

    resent_at = _LAST_SENT_AT + dt.timedelta(minutes=5)
    incremented = make_challenge(
        challenge_id=challenge_id,
        user_id=user_id,
        challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        expires_at=resent_at + dt.timedelta(minutes=15),
        last_sent_at=resent_at,
        attempts=3,
    )
    async with session_factory() as writer:
        await ChallengeRepository(session=writer).update_challenge_by_id(challenge_entity=incremented)
        await writer.commit()

    async with session_factory() as reader:
        found = await ChallengeRepository(session=reader).find_active_challenge_for_update(
            user_id=user_id,
            challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        )

    assert found is not None
    assert found.attempts == 3
    assert found.last_sent_at == resent_at
    assert found.expires_at == resent_at + dt.timedelta(minutes=15)


async def test_second_active_same_type_raises_integrity_error(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """Партиальный unique-индекс не даёт двух активных challenge'ей одного типа на пользователя."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="ch-unique@example.com", username="ch_unique")
    first = make_challenge(user_id=user_id, challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION, expires_at=_EXPIRES_AT)
    async with session_factory() as writer:
        await ChallengeRepository(session=writer).insert_challenge(challenge_entity=first)
        await writer.commit()

    second = make_challenge(
        user_id=user_id, challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION, expires_at=_EXPIRES_AT
    )
    async with session_factory() as writer:
        await ChallengeRepository(session=writer).insert_challenge(challenge_entity=second)
        with pytest.raises(IntegrityError):
            await writer.commit()


async def test_find_active_for_update_locks_row(
    session_factory: async_sessionmaker[AsyncSession],
    seed_user_credentials: Callable[..., Awaitable[None]],
) -> None:
    """``find_active_challenge_for_update`` берёт реальный row-лок: вторая сессия не возьмёт его под ``NOWAIT``."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="ch-lock@example.com", username="ch_lock")
    challenge_entity = make_challenge(
        user_id=user_id,
        challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        expires_at=_EXPIRES_AT,
    )
    async with session_factory() as writer:
        await ChallengeRepository(session=writer).insert_challenge(challenge_entity=challenge_entity)
        await writer.commit()

    async with session_factory() as holder, session_factory() as contender:
        # holder берёт row-лок через FOR UPDATE и держит транзакцию открытой
        locked = await ChallengeRepository(session=holder).find_active_challenge_for_update(
            user_id=user_id,
            challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        )
        assert locked is not None

        # тот же row под NOWAIT второй сессии недоступен → LockNotAvailable
        nowait_query = (
            sa.select(Challenge)
            .where(
                Challenge.user_id == user_id,
                Challenge.challenge_type == ChallengeTypeEnum.EMAIL_VERIFICATION.value,
                Challenge.used_at.is_(None),
            )
            .with_for_update(nowait=True)
        )
        with pytest.raises(OperationalError):
            await contender.execute(nowait_query)
