import pytest
from procrastinate import JobContext
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.backoffice.infra.repositories import AccountRepository
from app.shared.infra.db.postgres.component import SessionMaker
from app.shared.infra.di.registry import ComponentRegistry
from tests.builders import make_job_context


@pytest.fixture
def account_repository(db_session: AsyncSession) -> AccountRepository:
    return AccountRepository(db_session)


@pytest.fixture
def job_context(db_engine: AsyncEngine) -> JobContext:
    """``SessionMaker`` в реестре воркера смотрит в тестовый Postgres."""
    registry = ComponentRegistry()
    registry.set(key=SessionMaker, value=SessionMaker(db_engine, expire_on_commit=False))
    return make_job_context(registry=registry)
