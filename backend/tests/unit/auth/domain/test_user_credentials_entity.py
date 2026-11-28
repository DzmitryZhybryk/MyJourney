import datetime as dt
from uuid import UUID

import pytest

from app.auth.domain.entities import UserCredentialsEntity
from app.auth.domain.enums import UserPlanEnum, UserRoleEnum
from app.auth.exceptions import EmailAlreadyVerifiedError
from tests.builders import make_password, make_user_credentials


def test_create_defaults_to_user_role_free_plan_and_unverified() -> None:
    """Новая учётная запись — роль USER, тариф FREE, email не подтверждён."""
    user_credentials_entity = UserCredentialsEntity.create(
        email="user@example.com",
        username="user",
        password=make_password(),
    )

    assert user_credentials_entity.role is UserRoleEnum.USER
    assert user_credentials_entity.plan is UserPlanEnum.FREE
    assert user_credentials_entity.version == 1
    assert not user_credentials_entity.is_email_verified
    assert user_credentials_entity.email == "user@example.com"
    assert user_credentials_entity.username == "user"
    assert isinstance(user_credentials_entity.user_id, UUID)


def test_create_lowercases_email_and_keeps_username_case() -> None:
    """Email приводится к нижнему регистру, username остаётся как ввели."""
    user_credentials_entity = UserCredentialsEntity.create(
        email="Alice@Example.COM",
        username="Alice",
        password=make_password(),
    )

    assert user_credentials_entity.email == "alice@example.com"
    assert user_credentials_entity.username == "Alice"


def test_is_email_verified_reflects_timestamp() -> None:
    """Email подтверждён тогда и только тогда, когда задан ``email_verified_at``."""
    verified = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    unverified = make_user_credentials(email_verified_at=None)
    assert verified.is_email_verified
    assert not unverified.is_email_verified


def test_ensure_not_verified_verified_email_raises() -> None:
    """Email уже подтверждён → ``EmailAlreadyVerifiedError``."""
    user_credentials_entity = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    with pytest.raises(EmailAlreadyVerifiedError):
        user_credentials_entity.ensure_not_verified()


def test_ensure_not_verified_unverified_email_passes() -> None:
    """Email не подтверждён — ошибки нет."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    user_credentials_entity.ensure_not_verified()


def test_mark_email_verified_sets_timestamp_and_marks_updated() -> None:
    """Ставит ``email_verified_at`` и обновляет ``updated_at``."""
    user_credentials_entity = make_user_credentials(email_verified_at=None, updated_at=None)

    user_credentials_entity.mark_email_verified()

    assert user_credentials_entity.is_email_verified
    assert user_credentials_entity.email_verified_at is not None
    assert user_credentials_entity.updated_at is not None


def test_mark_email_verified_bumps_version_by_one() -> None:
    """Версия растёт ровно на единицу от прочитанной."""
    user_credentials_entity = make_user_credentials(email_verified_at=None, version=4)

    user_credentials_entity.mark_email_verified()

    assert user_credentials_entity.version == 5
