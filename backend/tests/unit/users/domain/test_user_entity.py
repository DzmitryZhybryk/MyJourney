import datetime as dt
from uuid import uuid4

import pytest

from app.users.domain.entities import UserEntity
from app.users.exceptions import UserDeletedError
from tests.builders import make_user_entity

_OLD_UPDATED_AT = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)


def test_create_sets_fields_and_defaults() -> None:
    """Создание проставляет переданные поля; ``deleted_at`` пуст."""
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
    assert user_entity.version == 1
    assert user_entity.deleted_at is None


def test_init_accepts_explicit_timestamps() -> None:
    """Конструктор принимает явные ``created_at``, ``updated_at`` и ``deleted_at``."""
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


def test_ensure_not_deleted_live_user_passes() -> None:
    """Неудалённый пользователь — ошибки нет, ``is_deleted`` ложно."""
    user_entity = make_user_entity()

    user_entity.ensure_not_deleted()

    assert user_entity.is_deleted is False


def test_ensure_not_deleted_soft_deleted_user_raises_user_deleted() -> None:
    """Задан ``deleted_at`` → ``UserDeletedError``, ``is_deleted`` истинно."""
    user_entity = make_user_entity(deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC))

    assert user_entity.is_deleted is True
    with pytest.raises(UserDeletedError):
        user_entity.ensure_not_deleted()


def test_update_profile_only_name_changes_name() -> None:
    """Только имя: имя меняется, согласие прежнее, ``updated_at`` сдвигается."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True, updated_at=_OLD_UPDATED_AT)

    user_entity.update_profile(display_name="Alice D.")

    assert user_entity.display_name == "Alice D."
    assert user_entity.marketing_emails_consent is True
    assert user_entity.updated_at != _OLD_UPDATED_AT


@pytest.mark.parametrize("consent", [True, False])
def test_update_profile_only_consent_changes_consent(consent: bool) -> None:
    """Только согласие: выставляется в обе стороны, имя прежнее."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=not consent)

    user_entity.update_profile(marketing_emails_consent=consent)

    assert user_entity.marketing_emails_consent is consent
    assert user_entity.display_name == "alice"


def test_update_profile_both_fields_changes_both() -> None:
    """Имя и согласие вместе — меняются оба."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=False)

    user_entity.update_profile(display_name="Alice D.", marketing_emails_consent=True)

    assert user_entity.display_name == "Alice D."
    assert user_entity.marketing_emails_consent is True


def test_update_profile_without_fields_touches_only_updated_at() -> None:
    """Без полей меняется только ``updated_at``."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True, updated_at=_OLD_UPDATED_AT)

    user_entity.update_profile()

    assert user_entity.display_name == "alice"
    assert user_entity.marketing_emails_consent is True
    assert user_entity.updated_at != _OLD_UPDATED_AT


def test_update_profile_bumps_version_by_one() -> None:
    """Версия растёт ровно на единицу от прочитанной."""
    user_entity = make_user_entity(version=3)

    user_entity.update_profile(display_name="Alice D.")

    assert user_entity.version == 4
