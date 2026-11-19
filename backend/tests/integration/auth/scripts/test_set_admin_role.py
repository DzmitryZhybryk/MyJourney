from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import psycopg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.domain.enums import UserRoleEnum
from app.auth.infra.repositories.user_credentials_repository import UserCredentialsRepository
from app.auth.scripts.set_admin_role import _set_admin_role
from app.shared.settings import PostgresSettings


async def _find_role(*, session_factory: async_sessionmaker[AsyncSession], user_id: UUID) -> UserRoleEnum:
    async with session_factory() as session:
        user_credentials_entity = await UserCredentialsRepository(session=session).find_user_credentials_by_user_id(
            user_id
        )
    assert user_credentials_entity is not None
    return user_credentials_entity.role


async def test_set_admin_role_promotes_account_found_by_email_in_any_case(
    seed_user_credentials: Callable[..., Awaitable[None]],
    session_factory: async_sessionmaker[AsyncSession],
    postgres_settings: PostgresSettings,
) -> None:
    """Аккаунт находится по email без учёта регистра и читается репозиторием как ADMIN; код выхода 0."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id, email="owner@example.com")

    with psycopg.connect(postgres_settings.postgres_libpq_dsn) as connection:
        exit_code = _set_admin_role(connection=connection, email="Owner@Example.com")

    assert exit_code == 0
    assert await _find_role(session_factory=session_factory, user_id=user_id) is UserRoleEnum.ADMIN


async def test_set_admin_role_when_admin_exists_refuses(
    seed_user_credentials: Callable[..., Awaitable[None]],
    session_factory: async_sessionmaker[AsyncSession],
    postgres_settings: PostgresSettings,
) -> None:
    """Админ уже есть → код выхода 1, второй аккаунт остаётся USER."""
    other_user_id = uuid4()
    await seed_user_credentials(email="admin@example.com", username="admin")
    await seed_user_credentials(user_id=other_user_id, email="other@example.com", username="other")

    with psycopg.connect(postgres_settings.postgres_libpq_dsn) as connection:
        _set_admin_role(connection=connection, email="admin@example.com")
        exit_code = _set_admin_role(connection=connection, email="other@example.com")

    assert exit_code == 1
    assert await _find_role(session_factory=session_factory, user_id=other_user_id) is UserRoleEnum.USER


async def test_set_admin_role_unknown_email_refuses(
    seed_user_credentials: Callable[..., Awaitable[None]],
    session_factory: async_sessionmaker[AsyncSession],
    postgres_settings: PostgresSettings,
) -> None:
    """Аккаунта с таким email нет → код выхода 1, существующий аккаунт не тронут."""
    user_id = uuid4()
    await seed_user_credentials(user_id=user_id)

    with psycopg.connect(postgres_settings.postgres_libpq_dsn) as connection:
        exit_code = _set_admin_role(connection=connection, email="missing@example.com")

    assert exit_code == 1
    assert await _find_role(session_factory=session_factory, user_id=user_id) is UserRoleEnum.USER
