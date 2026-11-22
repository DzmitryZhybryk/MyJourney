import datetime as dt
from uuid import uuid4

import pytest

from app.auth.application.schemas.commands import FindAccountsByIdsCommand
from app.auth.application.schemas.results import Account, CurrentAccountResult
from app.auth.application.services.account import AccountService
from app.auth.exceptions import AccountNotFoundError
from tests.builders import make_user_credentials
from tests.fakes import FakeAuthUnitOfWork, FakeUserCredentialsRepository


@pytest.mark.parametrize(
    ("email_verified_at", "expected_email_verified"),
    [
        (None, False),
        (dt.datetime(2026, 1, 1, tzinfo=dt.UTC), True),
    ],
)
async def test_get_current_account_returns_login_identifiers(
    account_service: AccountService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    email_verified_at: dt.datetime | None,
    expected_email_verified: bool,
) -> None:
    """get_current_account отдаёт email, username и статус подтверждения email учётной записи."""
    user_credentials_entity = make_user_credentials(
        email="neo@example.com",
        username="neo",
        email_verified_at=email_verified_at,
    )
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)

    result = await account_service.get_current_account(user_credentials_entity.user_id)

    assert result == CurrentAccountResult(
        email="neo@example.com",
        username="neo",
        email_verified=expected_email_verified,
    )


async def test_get_current_account_unknown_user_raises_account_not_found(
    account_service: AccountService,
    fake_uow: FakeAuthUnitOfWork,
) -> None:
    """get_current_account без учётной записи → AccountNotFoundError, без коммита."""
    with pytest.raises(AccountNotFoundError):
        await account_service.get_current_account(uuid4())

    fake_uow.commit_mock.assert_not_awaited()


async def test_find_accounts_by_ids_returns_found_and_deleted_and_skips_unknown(
    account_service: AccountService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_uow: FakeAuthUnitOfWork,
) -> None:
    """find_accounts_by_ids отдаёт живые и удалённые учётные записи с пометкой, а id без записи пропускает."""
    active_entity = make_user_credentials(email="neo@example.com", username="neo")
    deleted_entity = make_user_credentials(
        email="smith@example.com",
        username="smith",
        deleted_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )
    other_entity = make_user_credentials(email="trinity@example.com", username="trinity")
    for user_credentials_entity in (active_entity, deleted_entity, other_entity):
        await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)

    result = await account_service.find_accounts_by_ids(
        FindAccountsByIdsCommand(user_ids=frozenset({active_entity.user_id, deleted_entity.user_id, uuid4()})),
    )

    assert result.accounts == frozenset(
        {
            Account(id=active_entity.user_id, email="neo@example.com", is_deleted=False),
            Account(id=deleted_entity.user_id, email="smith@example.com", is_deleted=True),
        }
    )
    fake_uow.commit_mock.assert_not_awaited()
