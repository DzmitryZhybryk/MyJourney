import datetime as dt
from uuid import UUID

import pytest

from app.auth.domain.entities import UserCredentialsEntity
from app.auth.domain.enums import UserRoleEnum
from app.auth.exceptions import EmailAlreadyVerifiedError
from tests.builders import make_password, make_user_credentials


def test_create_defaults_to_free_role_and_unverified() -> None:
    """`create()` выдаёт роль FREE и неподтверждённый email."""
    creds = UserCredentialsEntity.create(
        email="user@example.com",
        username="user",
        password=make_password(),
    )

    assert creds.role is UserRoleEnum.FREE
    assert not creds.is_email_verified
    assert creds.email == "user@example.com"
    assert creds.username == "user"
    assert isinstance(creds.user_id, UUID)


def test_create_lowercases_email_and_keeps_username_case() -> None:
    """`create()` приводит email к нижнему регистру, username оставляет как ввели."""
    creds = UserCredentialsEntity.create(
        email="Alice@Example.COM",
        username="Alice",
        password=make_password(),
    )

    assert creds.email == "alice@example.com"
    assert creds.username == "Alice"


def test_is_email_verified_reflects_timestamp() -> None:
    """`is_email_verified` отражает наличие `email_verified_at`."""
    verified = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    unverified = make_user_credentials(email_verified_at=None)
    assert verified.is_email_verified
    assert not unverified.is_email_verified


def test_ensure_not_verified_raises_when_verified() -> None:
    """`ensure_not_verified` бросает, если email уже подтверждён."""
    creds = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    with pytest.raises(EmailAlreadyVerifiedError):
        creds.ensure_not_verified()


def test_ensure_not_verified_passes_when_unverified() -> None:
    """`ensure_not_verified` молчит для неподтверждённого email."""
    creds = make_user_credentials(email_verified_at=None)
    creds.ensure_not_verified()


def test_mark_email_verified_sets_timestamp_and_marks_updated() -> None:
    """`mark_email_verified` ставит timestamp и обновляет `updated_at`."""
    creds = make_user_credentials(email_verified_at=None, updated_at=None)

    creds.mark_email_verified()

    assert creds.is_email_verified
    assert creds.email_verified_at is not None
    assert creds.updated_at is not None
