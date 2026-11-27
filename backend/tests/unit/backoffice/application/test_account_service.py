from uuid import UUID

from app.backoffice.application.ports.account_repository import AccountListItem
from app.backoffice.application.schemas.commands import (
    ApplyAccountChangedCommand,
    ApplyProfileChangedCommand,
    ListAccountsCommand,
)
from app.backoffice.application.schemas.results import ListAccountsResult
from app.backoffice.application.services.account import AccountService
from app.shared.enums import SortDirectionEnum
from app.shared.pagination.offset import OffsetPage, OffsetPageQuery
from tests.builders import make_account_auth_part, make_account_filters, make_account_profile_part
from tests.fakes import AccountsPageQuery, FakeAccountRepository, FakeBackofficeUnitOfWork


async def test_apply_account_changed_writes_auth_part_and_commits(
    account_service: AccountService,
    fake_account_repository: FakeAccountRepository,
    fake_backoffice_uow: FakeBackofficeUnitOfWork,
) -> None:
    """Снимок учётной записи записывается в строку аккаунта и коммитится."""
    auth_part = make_account_auth_part(email="neo@example.com", version=2)

    await account_service.apply_account_changed(
        user_id=UUID(int=1),
        command=ApplyAccountChangedCommand(auth_part=auth_part),
    )

    assert fake_account_repository.auth_parts == {UUID(int=1): auth_part}
    assert fake_account_repository.profile_parts == {}
    fake_backoffice_uow.commit_mock.assert_awaited_once()


async def test_apply_profile_changed_writes_profile_part_and_commits(
    account_service: AccountService,
    fake_account_repository: FakeAccountRepository,
    fake_backoffice_uow: FakeBackofficeUnitOfWork,
) -> None:
    """Снимок профиля записывается в строку аккаунта и коммитится."""
    profile_part = make_account_profile_part(display_name="Neo", version=3)

    await account_service.apply_profile_changed(
        user_id=UUID(int=1),
        command=ApplyProfileChangedCommand(profile_part=profile_part),
    )

    assert fake_account_repository.profile_parts == {UUID(int=1): profile_part}
    assert fake_account_repository.auth_parts == {}
    fake_backoffice_uow.commit_mock.assert_awaited_once()


async def test_list_accounts_passes_query_and_returns_page_without_commit(
    account_service: AccountService,
    fake_account_repository: FakeAccountRepository,
    fake_backoffice_uow: FakeBackofficeUnitOfWork,
) -> None:
    """Список передаёт хранилищу страницу, фильтр и направление и отдаёт его страницу и total; чтение не коммитит."""
    account_item = AccountListItem(
        user_id=UUID(int=1),
        email="neo@example.com",
        username=None,
        role=None,
        plan=None,
        email_verified_at=None,
        registered_at=None,
        deleted_at=None,
        display_name=None,
        marketing_emails_consent=None,
        terms_accepted_at=None,
    )
    fake_account_repository.accounts_page = OffsetPage(items=(account_item,), total=41)
    command = ListAccountsCommand(
        page=OffsetPageQuery(page=3, limit=20),
        filters=make_account_filters(email_contains="neo", role="admin", include_deleted=True),
        sort_direction=SortDirectionEnum.ASC,
    )

    result = await account_service.list_accounts(command)

    assert result == ListAccountsResult(items=(account_item,), total=41)
    assert fake_account_repository.page_queries == [
        AccountsPageQuery(page=command.page, filters=command.filters, sort_direction=SortDirectionEnum.ASC),
    ]
    fake_backoffice_uow.commit_mock.assert_not_awaited()
