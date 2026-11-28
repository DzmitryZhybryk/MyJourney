"""Фейки портов backoffice: хранилище строк списка аккаунтов и его UoW."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import UUID

from app.backoffice.application.ports.account_repository import (
    AccountAuthPart,
    AccountFilters,
    AccountListItem,
    AccountProfilePart,
    AccountRepositoryPort,
)
from app.backoffice.application.ports.unit_of_work import BackofficeUnitOfWorkPort
from app.shared.enums import SortDirectionEnum
from app.shared.pagination.offset import OffsetPage, OffsetPageQuery


@dataclass(frozen=True, slots=True)
class AccountsPageQuery:
    """Аргументы одного запроса страницы к фейку — чтобы тест проверил, что сервис их передал."""

    page: OffsetPageQuery
    filters: AccountFilters
    sort_direction: SortDirectionEnum


class FakeAccountRepository(AccountRepositoryPort):
    """
    Фейк хранилища строк списка: части пишутся в словари по ``user_id`` (последняя побеждает — версии
    сравнивает SQL, его проверяет integration), страницу отдаёт заданную тестом в ``accounts_page``.
    """

    def __init__(self) -> None:
        self.auth_parts: dict[UUID, AccountAuthPart] = {}
        self.profile_parts: dict[UUID, AccountProfilePart] = {}
        self.accounts_page: OffsetPage[AccountListItem] = OffsetPage(items=(), total=0)
        self.page_queries: list[AccountsPageQuery] = []

    async def upsert_account_auth_part(self, *, user_id: UUID, auth_part: AccountAuthPart) -> None:
        self.auth_parts[user_id] = auth_part

    async def upsert_account_profile_part(self, *, user_id: UUID, profile_part: AccountProfilePart) -> None:
        self.profile_parts[user_id] = profile_part

    async def find_accounts_page(
        self,
        *,
        page: OffsetPageQuery,
        filters: AccountFilters,
        sort_direction: SortDirectionEnum,
    ) -> OffsetPage[AccountListItem]:
        self.page_queries.append(AccountsPageQuery(page=page, filters=filters, sort_direction=sort_direction))
        return self.accounts_page


class FakeBackofficeUnitOfWork(BackofficeUnitOfWorkPort):
    """In-memory UoW backoffice: фейк-репозиторий снаружи, мокнутый ``commit`` и no-op ``transaction``."""

    def __init__(self, account_repository: AccountRepositoryPort) -> None:
        self.account_repository = account_repository
        self.commit_mock = AsyncMock()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        yield

    async def commit(self) -> None:
        await self.commit_mock()
