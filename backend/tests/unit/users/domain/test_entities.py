import datetime as dt
from uuid import uuid4

import pytest

from app.users.domain.entities import UserEntity
from app.users.exceptions import UserDeletedError
from tests.builders import make_user_entity


def test_user_entity_create_sets_fields_and_defaults() -> None:
    """Фабрика `create` проставляет переданные поля; deleted_at — None."""
    user_id = uuid4()
    terms_accepted_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)

    user_entity = UserEntity.create(
        user_id=user_id,
        display_name="alice",
        marketing_emails_consent=True,
        terms_accepted_at=terms_accepted_at,
    )

    assert user_entity.user_id == user_id
    assert user_entity.display_name == "alice"
    assert user_entity.marketing_emails_consent is True
    assert user_entity.terms_accepted_at == terms_accepted_at
    assert user_entity.deleted_at is None


def test_user_entity_accepts_explicit_timestamps() -> None:
    """Конструктор принимает явные timestamp'ы (created/updated/deleted)."""
    created_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    updated_at = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
    deleted_at = dt.datetime(2026, 1, 3, tzinfo=dt.UTC)

    user_entity = make_user_entity(
        created_at=created_at,
        updated_at=updated_at,
        deleted_at=deleted_at,
    )

    assert user_entity.created_at == created_at
    assert user_entity.updated_at == updated_at
    assert user_entity.deleted_at == deleted_at


def test_user_entity_ensure_not_deleted_passes_for_active_user() -> None:
    """`ensure_not_deleted` молчит для неудалённого пользователя; is_deleted — False."""
    user_entity = make_user_entity()

    user_entity.ensure_not_deleted()

    assert user_entity.is_deleted is False


def test_user_entity_ensure_not_deleted_raises_for_soft_deleted_user() -> None:
    """`ensure_not_deleted` бросает UserDeletedError при выставленном deleted_at; is_deleted — True."""
    user_entity = make_user_entity(deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC))

    assert user_entity.is_deleted is True
    with pytest.raises(UserDeletedError):
        user_entity.ensure_not_deleted()
