"""Транзакционную модель проверяет ``integration/shared/infra/db/postgres/test_uow.py``; здесь — проводка UoW."""

from typing import Final
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.backoffice.infra.models import Account
from app.backoffice.infra.uow import BackofficeUnitOfWork
from tests.builders import make_account_auth_part

_COUNT_ACCOUNTS: Final[sa.Select[int]] = sa.select(sa.func.count()).select_from(Account)


async def test_account_repository_write_is_persisted_by_uow_commit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Запись через ``uow.account_repository`` фиксирует ``uow.commit()`` — она видна из новой сессии."""
    async with session_factory() as session:
        uow = BackofficeUnitOfWork(session)
        async with uow.transaction():
            await uow.account_repository.upsert_account_auth_part(user_id=uuid4(), auth_part=make_account_auth_part())
            await uow.commit()

    async with session_factory() as reader:
        count = (await reader.execute(_COUNT_ACCOUNTS)).scalar_one()

    assert count == 1
