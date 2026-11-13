"""
Интеграционный харнесс: реальный Postgres в testcontainers.

**Схема** создаётся из ``BaseDBModel.metadata`` (источник истины; миграция
``e00067cc5c0e`` отражает её 1:1 — проверено: партиальный unique-индекс
challenges, FK-цепочка и unique-индексы по ``lower()`` живут в моделях) **синхронным**
движком на старте сессии — без event loop, чтобы не упираться в loop-scope
``pytest-asyncio`` (главная боль session-scoped async-фикстур: psycopg3-async
соединение привязано к loop'у, в котором создано).

**Изоляция** между тестами — TRUNCATE всех таблиц на входе в ``db_engine``:
чистый старт независимо от того, коммитил ли прошлый тест. Движок и сессии —
function-scoped: создаются и закрываются в одном function-loop'е, поэтому
async-соединения не «утекают» между event loop'ами.

**FK-цепочка**: ``refresh_tokens`` / ``challenges`` → ``user_credentials.user_id``.
Перед вставкой токена/challenge'а сидируй учётку через ``seed_user_credentials``.
"""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from uuid import UUID

import pytest
import sqlalchemy as sa
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

# Импорт моделей регистрирует таблицы в ``BaseDBModel.metadata`` (нужно для create_all).
from app.auth.infra import models as _auth_models  # noqa: F401
from app.auth.infra.repositories import UserCredentialsRepository
from app.geo.infra import models as _geo_models  # noqa: F401
from app.journeys.infra import models as _journey_models  # noqa: F401
from app.shared.models import BaseDBModel
from app.shared.settings import PostgresSettings
from app.users.domain.entities import UserEntity  # noqa: F401 — гарантирует регистрацию users-модели
from app.users.infra import models as _users_models  # noqa: F401
from tests.builders import make_user_credentials

_POSTGRES_IMAGE = "postgres:17-alpine"
# Порядок не важен: ``TRUNCATE ... CASCADE`` снимает FK-зависимости разом.
_ALL_TABLES = (
    "users",
    "user_credentials",
    "refresh_tokens",
    "challenges",
    "geo_cities",
    "geo_places",
    "geo_dataset_loads",
    "journeys",
)


@pytest.fixture(scope="session")
def _postgres_container() -> Iterator[PostgresContainer]:
    """Поднимает PG-контейнер на всю сессию и создаёт схему синхронно (без event loop)."""
    with PostgresContainer(_POSTGRES_IMAGE, driver="psycopg") as container:
        sync_engine = create_engine(container.get_connection_url())
        try:
            BaseDBModel.metadata.create_all(sync_engine)
        finally:
            sync_engine.dispose()

        yield container


@pytest.fixture
async def db_engine(_postgres_container: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    """
    Async-движок на контейнерный DSN, чистый на каждый тест.

    Function-scoped: создаётся и закрывается в том же loop'е, что и тест. TRUNCATE на
    входе гарантирует пустую схему независимо от того, коммитил ли прошлый тест.
    ``NullPool`` — каждая сессия берёт собственное соединение (нужно для тестов с
    двумя конкурентными сессиями и row-локами).
    """
    engine = create_async_engine(_postgres_container.get_connection_url(), poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(sa.text(f"TRUNCATE {', '.join(_ALL_TABLES)} CASCADE"))

    yield engine
    await engine.dispose()


@pytest.fixture
def postgres_settings(_postgres_container: PostgresContainer) -> PostgresSettings:
    """``PostgresSettings`` на параметры контейнера — для тестов lifecycle (``SqlAlchemyComponent``)."""
    return PostgresSettings(
        POSTGRES_USER=_postgres_container.username,
        POSTGRES_PASSWORD=SecretStr(_postgres_container.password),
        POSTGRES_DB=_postgres_container.dbname,
        POSTGRES_HOST=_postgres_container.get_container_host_ip(),
        POSTGRES_PORT=int(_postgres_container.get_exposed_port(5432)),
    )


@pytest.fixture
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Фабрика сессий поверх контейнерного движка (``expire_on_commit=False`` — как в проде)."""
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Одна async-сессия для одно-сессионных тестов (insert→find, update, констрейнты)."""
    async with session_factory() as session:
        yield session


@pytest.fixture
def seed_user_credentials(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[..., Awaitable[None]]:
    """
    Коммитит учётку — FK-родителя для ``refresh_tokens`` / ``challenges``.

    Возвращает async-callable: ``await seed_user_credentials(user_id=..., email=...)``.
    Дефолты — из ``make_user_credentials``; тест переопределяет нужное (для двух
    учёток дай разные ``email``/``username`` — оба поля уникальны).
    """

    async def _seed(
        *,
        user_id: UUID | None = None,
        email: str = "user@example.com",
        username: str = "user",
    ) -> None:
        user_credentials_entity = make_user_credentials(user_id=user_id, email=email, username=username)
        async with session_factory() as session:
            repository = UserCredentialsRepository(session=session)
            await repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
            await session.commit()

    return _seed
