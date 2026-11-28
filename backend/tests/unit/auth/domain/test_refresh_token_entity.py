import datetime as dt

from tests.builders import make_refresh_token


def test_is_expired_past_expiry_is_true() -> None:
    """Срок действия в прошлом — токен истёк."""
    refresh_token_entity = make_refresh_token(expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1))
    assert refresh_token_entity.is_expired


def test_is_expired_future_expiry_is_false() -> None:
    """Срок действия в будущем — токен не истёк."""
    refresh_token_entity = make_refresh_token(expires_at=dt.datetime.now(tz=dt.UTC) + dt.timedelta(days=1))
    assert not refresh_token_entity.is_expired


def test_is_revoked_reflects_revoked_at() -> None:
    """Токен отозван тогда и только тогда, когда задан ``revoked_at``."""
    active = make_refresh_token(revoked_at=None)
    revoked = make_refresh_token(revoked_at=dt.datetime.now(tz=dt.UTC))
    assert not active.is_revoked
    assert revoked.is_revoked


def test_revoke_sets_revoked_at_and_marks_updated() -> None:
    """Ставит ``revoked_at`` и обновляет ``updated_at``."""
    refresh_token_entity = make_refresh_token(revoked_at=None, updated_at=None)

    refresh_token_entity.revoke()

    assert refresh_token_entity.is_revoked
    assert refresh_token_entity.revoked_at is not None
    assert refresh_token_entity.updated_at is not None


def test_revoke_is_idempotent() -> None:
    """Повторный отзыв не перезаписывает ``revoked_at``."""
    revoked_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(hours=1)
    refresh_token_entity = make_refresh_token(revoked_at=revoked_at)

    refresh_token_entity.revoke()

    assert refresh_token_entity.revoked_at == revoked_at
