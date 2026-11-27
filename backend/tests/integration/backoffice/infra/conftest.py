"""Фикстуры infra-слоя backoffice: репозиторий на сессии теста и ``JobContext`` для тасок проекции."""

import pytest
from procrastinate import App, JobContext
from procrastinate.testing import InMemoryConnector
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.backoffice.infra.repositories import AccountRepository
from app.shared.infra.db.postgres.component import SessionMaker
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.procrastinate.component import WORKER_REGISTRY_KEY
from tests.builders import make_job


@pytest.fixture
def account_repository(db_session: AsyncSession) -> AccountRepository:
    return AccountRepository(db_session)


@pytest.fixture
def job_context(db_engine: AsyncEngine) -> JobContext:
    """``JobContext`` с реестром воркера, где ``SessionMaker`` смотрит в тестовый Postgres."""
    registry = ComponentRegistry()
    registry.set(key=SessionMaker, value=SessionMaker(db_engine, expire_on_commit=False))
    return JobContext(
        app=App(connector=InMemoryConnector()),
        job=make_job(),
        start_timestamp=0.0,
        abort_reason=lambda: None,
        additional_context={WORKER_REGISTRY_KEY: registry},
    )
