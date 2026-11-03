"""
Интеграционные тесты ``UserCredentialsRepository`` против реального Postgres.

Покрывают round-trip entity↔БД, поиск по email/username без учёта регистра и реальные
unique-индексы по ``lower(email)`` / ``lower(username)``, которые на фейках не проверить.
"""

import datetime as dt
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.domain.enums import UserRoleEnum
from app.auth.infra.repositories import UserCredentialsRepository
from tests.builders import make_user_credentials

_VERIFIED_AT = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)


async def test_insert_then_find_by_user_id_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """insert + commit → ``find_user_credentials_by_user_id`` возвращает ту же сущность."""
    user_id = uuid4()
    user_credentials_entity = make_user_credentials(
        user_id=user_id, email="uc-roundtrip@example.com", username="uc_roundtrip"
    )
    async with session_factory() as writer:
        await UserCredentialsRepository(session=writer).insert_user_credentials(
            user_credentials_entity=user_credentials_entity
        )
        await writer.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(session=reader).find_user_credentials_by_user_id(user_id=user_id)

    assert found is not None
    assert found.user_id == user_id
    assert found.email == "uc-roundtrip@example.com"
    assert found.username == "uc_roundtrip"
    assert found.password.hash == user_credentials_entity.password.hash
    assert found.role is UserRoleEnum.FREE
    assert found.email_verified_at is None


@pytest.mark.parametrize("lookup_email", ["first@example.com", "FIRST@EXAMPLE.COM", "First@Example.com"])
async def test_find_by_email_ignores_case(
    session_factory: async_sessionmaker[AsyncSession],
    lookup_email: str,
) -> None:
    """``find_user_credentials_by_email`` находит запись в любом регистре и не задевает соседей."""
    user_id = uuid4()
    async with session_factory() as writer:
        repository = UserCredentialsRepository(session=writer)
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(user_id=user_id, email="first@example.com", username="first")
        )
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(email="second@example.com", username="second")
        )
        await writer.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(session=reader).find_user_credentials_by_email(email=lookup_email)

    assert found is not None
    assert found.user_id == user_id


@pytest.mark.parametrize("lookup_username", ["Neo", "neo", "NEO"])
async def test_find_by_username_ignores_case(
    session_factory: async_sessionmaker[AsyncSession],
    lookup_username: str,
) -> None:
    """``find_user_credentials_by_username`` находит запись в любом регистре и не задевает соседей."""
    user_id = uuid4()
    async with session_factory() as writer:
        repository = UserCredentialsRepository(session=writer)
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(user_id=user_id, email="neo@example.com", username="Neo")
        )
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(email="trinity@example.com", username="Trinity")
        )
        await writer.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(session=reader).find_user_credentials_by_username(
            username=lookup_username
        )

    assert found is not None
    assert found.user_id == user_id


@pytest.mark.parametrize("login", ["neo@example.com", "NEO@Example.com", "neo", "NEO"])
async def test_find_by_login_matches_email_or_username_ignoring_case(
    session_factory: async_sessionmaker[AsyncSession],
    login: str,
) -> None:
    """``find_user_credentials_by_login`` находит учётку и по email, и по username в любом регистре."""
    user_id = uuid4()
    async with session_factory() as writer:
        repository = UserCredentialsRepository(session=writer)
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(user_id=user_id, email="neo@example.com", username="Neo")
        )
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(email="trinity@example.com", username="Trinity")
        )
        await writer.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(session=reader).find_user_credentials_by_login(login=login)

    assert found is not None
    assert found.user_id == user_id


async def test_find_by_login_prefers_email_owner_over_matching_username(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Логин — чей-то email и одновременно чужой username → возвращается владелец email."""
    email_owner_id = uuid4()
    async with session_factory() as writer:
        repository = UserCredentialsRepository(session=writer)
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(
                user_id=email_owner_id, email="bob@example.com", username="bob"
            )
        )
        await repository.insert_user_credentials(
            user_credentials_entity=make_user_credentials(email="other@example.com", username="bob@example.com")
        )
        await writer.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(session=reader).find_user_credentials_by_login(login="BOB@example.com")

    assert found is not None
    assert found.user_id == email_owner_id


async def test_find_by_email_username_and_login_no_match_returns_none(db_session: AsyncSession) -> None:
    """Поиск без совпадений возвращает ``None``, а не падает."""
    repository = UserCredentialsRepository(session=db_session)

    assert await repository.find_user_credentials_by_email(email="nobody@example.com") is None
    assert await repository.find_user_credentials_by_username(username="nobody") is None
    assert await repository.find_user_credentials_by_login(login="nobody") is None


async def test_insert_email_differing_only_by_case_raises_integrity_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Email, отличающийся только регистром, нарушает unique-индекс по lower(email) — ``IntegrityError``."""
    existing = make_user_credentials(email="dup@example.com", username="original_user")
    async with session_factory() as writer:
        await UserCredentialsRepository(session=writer).insert_user_credentials(user_credentials_entity=existing)
        await writer.commit()

    duplicate = make_user_credentials(email="DUP@Example.com", username="another_user")
    async with session_factory() as writer:
        await UserCredentialsRepository(session=writer).insert_user_credentials(user_credentials_entity=duplicate)
        with pytest.raises(IntegrityError):
            await writer.commit()


async def test_insert_username_differing_only_by_case_raises_integrity_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Username, отличающийся только регистром, нарушает unique-индекс по lower(username) — ``IntegrityError``."""
    existing = make_user_credentials(email="original@example.com", username="dup_user")
    async with session_factory() as writer:
        await UserCredentialsRepository(session=writer).insert_user_credentials(user_credentials_entity=existing)
        await writer.commit()

    duplicate = make_user_credentials(email="another@example.com", username="DUP_User")
    async with session_factory() as writer:
        await UserCredentialsRepository(session=writer).insert_user_credentials(user_credentials_entity=duplicate)
        with pytest.raises(IntegrityError):
            await writer.commit()


async def test_update_persists_email_verified_at(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """``update_user_credentials_by_user_id`` персистит ``email_verified_at`` (виден из новой сессии)."""
    user_id = uuid4()
    user_credentials_entity = make_user_credentials(
        user_id=user_id, email="uc-update@example.com", username="uc_update"
    )
    async with session_factory() as writer:
        await UserCredentialsRepository(session=writer).insert_user_credentials(
            user_credentials_entity=user_credentials_entity
        )
        await writer.commit()

    verified = make_user_credentials(
        user_id=user_id,
        email="uc-update@example.com",
        username="uc_update",
        email_verified_at=_VERIFIED_AT,
    )
    async with session_factory() as writer:
        await UserCredentialsRepository(session=writer).update_user_credentials_by_user_id(
            user_credentials_entity=verified
        )
        await writer.commit()

    async with session_factory() as reader:
        found = await UserCredentialsRepository(session=reader).find_user_credentials_by_user_id(user_id=user_id)

    assert found is not None
    assert found.email_verified_at == _VERIFIED_AT
