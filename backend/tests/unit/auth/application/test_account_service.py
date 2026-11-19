import datetime as dt
from uuid import uuid4

import pytest

from app.auth.application.schemas.results import CurrentAccountResult
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
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)

    result = await account_service.get_current_account(user_id=user_credentials_entity.user_id)

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
        await account_service.get_current_account(user_id=uuid4())

    fake_uow.commit_mock.assert_not_awaited()
