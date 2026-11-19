"""
Unit-тест ``ProcrastinateComponent.startup`` при недоступной базе.

Коннектор procrastinate присваивает себе пул до ожидания первых соединений. На таймауте
psycopg_pool закрывает пул сам, а при отмене ожидания — нет, поэтому прерванный старт оставил бы
пул открытым. Сеть не нужна: подменяется только внешний слой — открытие пула psycopg прерывается
отменой, как при SIGINT во время ожидания, а закрытие пула записывается.
"""

import asyncio

import psycopg_pool
import pytest
from pydantic import SecretStr

from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.procrastinate.component import ProcrastinateApp, ProcrastinateComponent
from app.shared.settings import ProcrastinateSettings


async def test_startup_cancelled_pool_open_closes_pool_and_registers_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ожидание пула отменено: startup пробрасывает отмену, пул закрыт, ``ProcrastinateApp`` в реестр не попал."""
    closed_pools: list[psycopg_pool.AsyncConnectionPool] = []
    original_close = psycopg_pool.AsyncConnectionPool.close

    async def failing_open(self: psycopg_pool.AsyncConnectionPool, **_kwargs: object) -> None:
        raise asyncio.CancelledError

    async def recording_close(self: psycopg_pool.AsyncConnectionPool) -> None:
        closed_pools.append(self)
        await original_close(self)

    monkeypatch.setattr(psycopg_pool.AsyncConnectionPool, "open", failing_open)
    monkeypatch.setattr(psycopg_pool.AsyncConnectionPool, "close", recording_close)
    component = ProcrastinateComponent(
        settings=ProcrastinateSettings(POSTGRES_USER="user", POSTGRES_PASSWORD=SecretStr("pw"), POSTGRES_DB="db"),
    )
    registry = ComponentRegistry()

    with pytest.raises(asyncio.CancelledError):
        await component.startup(registry)

    assert len(closed_pools) == 1
    assert ProcrastinateApp not in registry
