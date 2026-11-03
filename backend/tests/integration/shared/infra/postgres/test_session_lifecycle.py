"""
Интеграционные тесты lifecycle PG-инфраструктуры против реального Postgres.

Покрывают то, что api-тесты обходят (там сессия подменена фейком): сборку движка
и регистрацию ``SessionMaker`` в ``SqlAlchemyComponent`` (startup/shutdown) и
выдачу рабочей сессии зависимостью ``db_session_dependency``.
"""

from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.requests import Request

from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.postgres.component import SessionMaker, SqlAlchemyComponent
from app.shared.infra.postgres.dependency import db_session_dependency
from app.shared.settings import PostgresSettings


async def test_sqlalchemy_component_startup_registers_working_sessionmaker(
    postgres_settings: PostgresSettings,
) -> None:
    """``startup`` регистрирует ``SessionMaker`` в registry, а его сессия реально ходит в БД."""
    component = SqlAlchemyComponent(settings=postgres_settings)
    registry = ComponentRegistry()
    try:
        await component.startup(registry)
        session_maker = registry.get(SessionMaker)
        async with session_maker() as session:
            result = await session.execute(sa.text("SELECT 1"))

        assert result.scalar_one() == 1
    finally:
        await component.shutdown()


async def test_db_session_dependency_yields_working_session(db_engine: AsyncEngine) -> None:
    """``db_session_dependency`` достаёт ``SessionMaker`` из ``request.app.registry`` и отдаёт рабочую сессию."""
    registry = ComponentRegistry()
    registry.set(key=SessionMaker, value=SessionMaker(db_engine, expire_on_commit=False))
    scope: dict[str, Any] = {"type": "http", "app": SimpleNamespace(registry=registry)}
    request = Request(scope)

    generator = db_session_dependency(request=request)
    session = await anext(generator)
    try:
        result = await session.execute(sa.text("SELECT 1"))
        assert result.scalar_one() == 1
    finally:
        # исчерпание генератора закрывает сессию (выход из ``async with sessionmaker()``)
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
