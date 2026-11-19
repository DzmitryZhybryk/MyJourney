"""
Интеграционные тесты ``BaseUnitOfWork`` против реального Postgres.

Транзакционная модель общая для всех доменных UoW и проверяется здесь один раз, на пробной
таблице: ``commit()`` внутри ``transaction()`` делает запись видимой другим сессиям, а выход
без commit'а и исключение её откатывают. Доменные ``test_uow.py`` проверяют только сборку
своего UoW.
"""

from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.infra.postgres.uow import BaseUnitOfWork


async def test_transaction_commit_persists_across_sessions(
    session_factory: async_sessionmaker[AsyncSession],
    uow_probe_table: sa.Table,
) -> None:
    """``commit()`` внутри ``transaction()`` фиксирует запись — она видна из новой сессии."""
    row_id = uuid4()
    async with session_factory() as session:
        uow = BaseUnitOfWork(session=session)
        async with uow.transaction():
            await uow.session.execute(sa.insert(uow_probe_table).values(id=row_id))
            await uow.commit()

    async with session_factory() as reader:
        found = await reader.scalar(sa.select(uow_probe_table.c.id).where(uow_probe_table.c.id == row_id))

    assert found == row_id


async def test_transaction_without_commit_rolls_back(
    session_factory: async_sessionmaker[AsyncSession],
    uow_probe_table: sa.Table,
) -> None:
    """Выход из ``transaction()`` без ``commit()`` откатывает запись — commit после выхода её не сохраняет."""
    row_id = uuid4()
    async with session_factory() as session:
        uow = BaseUnitOfWork(session=session)
        async with uow.transaction():
            await uow.session.execute(sa.insert(uow_probe_table).values(id=row_id))
        # Без rollback'а на выходе из transaction() этот commit сохранил бы запись.
        await uow.commit()

    async with session_factory() as reader:
        found = await reader.scalar(sa.select(uow_probe_table.c.id).where(uow_probe_table.c.id == row_id))

    assert found is None


async def test_exception_in_transaction_rolls_back(
    session_factory: async_sessionmaker[AsyncSession],
    uow_probe_table: sa.Table,
) -> None:
    """Исключение внутри ``transaction()`` пробрасывается и откатывает незакоммиченную запись."""
    row_id = uuid4()
    async with session_factory() as session:
        uow = BaseUnitOfWork(session=session)
        # PT012: блок намеренно составной — проверяем, что исключение проходит сквозь
        # transaction() (и откатывает), поэтому raise обязан быть внутри async with.
        with pytest.raises(RuntimeError, match="boom"):  # noqa: PT012
            async with uow.transaction():
                await uow.session.execute(sa.insert(uow_probe_table).values(id=row_id))
                raise RuntimeError("boom")
        # Без rollback'а на выходе из transaction() этот commit сохранил бы запись.
        await uow.commit()

    async with session_factory() as reader:
        found = await reader.scalar(sa.select(uow_probe_table.c.id).where(uow_probe_table.c.id == row_id))

    assert found is None


async def test_session_property_returns_underlying_session(db_session: AsyncSession) -> None:
    """``session``-property отдаёт ту же сессию — шов для atomic-defer (``task_bus.bind_to(uow.session)``)."""
    uow = BaseUnitOfWork(session=db_session)

    assert uow.session is db_session
