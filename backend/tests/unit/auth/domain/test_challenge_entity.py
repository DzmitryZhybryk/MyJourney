import datetime as dt
from uuid import uuid4

import pytest

from app.auth.domain.entities import ChallengeEntity
from app.auth.domain.enums import ChallengeTypeEnum
from app.auth.exceptions import (
    ChallengeAttemptsExceededError,
    ChallengeExpiredError,
    ChallengeResendCooldownError,
)
from tests.builders import make_challenge


def test_generate_code_is_six_digits() -> None:
    """`generate_code` возвращает строку из 6 цифр."""
    code = ChallengeEntity.generate_code()
    assert len(code) == 6
    assert code.isdigit()


def test_is_active_true_when_unused_and_not_expired() -> None:
    """`is_active` истинно для неиспользованного и не истёкшего challenge'а."""
    challenge_entity = make_challenge(
        used_at=None,
        expires_at=dt.datetime.now(tz=dt.UTC) + dt.timedelta(minutes=10),
    )
    assert challenge_entity.is_active()


def test_is_active_false_when_used() -> None:
    """`is_active` ложно для уже использованного challenge'а."""
    challenge_entity = make_challenge(used_at=dt.datetime.now(tz=dt.UTC))
    assert not challenge_entity.is_active()


def test_is_active_false_when_expired() -> None:
    """`is_active` ложно для истёкшего challenge'а."""
    challenge_entity = make_challenge(expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1))
    assert not challenge_entity.is_active()


def test_create_starts_ttl_from_first_send() -> None:
    """`create` отмечает первую отправку и отсчитывает срок от неё."""
    challenge_entity = ChallengeEntity.create(
        user_id=uuid4(),
        challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        code_ciphertext="ciphertext",
        ttl_minutes=15,
    )

    assert challenge_entity.expires_at == challenge_entity.last_sent_at + dt.timedelta(minutes=15)


def test_is_expired_false_before_and_true_after_expires_at() -> None:
    """`is_expired` ложно до `expires_at` и истинно после."""
    now = dt.datetime.now(tz=dt.UTC)

    assert not make_challenge(expires_at=now + dt.timedelta(minutes=1)).is_expired()
    assert make_challenge(expires_at=now - dt.timedelta(seconds=1)).is_expired()


def test_seconds_until_expiry_rounds_up() -> None:
    """Остаток до истечения — целые секунды вверх: 90 с без долей не превращаются в 89."""
    challenge_entity = make_challenge(expires_at=dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=90))

    assert challenge_entity.seconds_until_expiry() == 90


def test_seconds_until_expiry_is_zero_when_expired() -> None:
    """У истёкшего кода остаток — ноль, а не отрицательное число."""
    challenge_entity = make_challenge(expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=5))

    assert challenge_entity.seconds_until_expiry() == 0


def test_ensure_resend_cooldown_passed_raises_within_cooldown() -> None:
    """Бросает, если с последней отправки прошло меньше cooldown'а, хотя код создан давно."""
    now = dt.datetime.now(tz=dt.UTC)
    challenge_entity = make_challenge(
        created_at=now - dt.timedelta(minutes=10),
        last_sent_at=now - dt.timedelta(seconds=10),
    )

    with pytest.raises(ChallengeResendCooldownError):
        challenge_entity.ensure_resend_cooldown_passed(cooldown_seconds=60)


def test_ensure_resend_cooldown_passed_ok_after_cooldown() -> None:
    """Молчит, когда с последней отправки прошёл cooldown."""
    challenge_entity = make_challenge(last_sent_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=120))

    challenge_entity.ensure_resend_cooldown_passed(cooldown_seconds=60)


def test_ensure_not_exhausted_raises_with_seconds_until_expiry() -> None:
    """Исчерпанные попытки → 429 с секундами до истечения кода в `details`."""
    challenge_entity = make_challenge(
        attempts=5,
        expires_at=dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=540),
    )

    with pytest.raises(ChallengeAttemptsExceededError) as exc_info:
        challenge_entity.ensure_not_exhausted(max_attempts=5)

    assert exc_info.value.details == {"retry_after_seconds": 540}


def test_ensure_not_exhausted_ok_with_attempts_left() -> None:
    """Молчит, пока попытки остались."""
    challenge_entity = make_challenge(attempts=4)

    challenge_entity.ensure_not_exhausted(max_attempts=5)


def test_resend_moves_last_sent_and_extends_expiry() -> None:
    """`resend` отмечает отправку сейчас, продлевает срок на TTL от неё и обновляет `updated_at`."""
    old_sent_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=5)
    challenge_entity = make_challenge(
        last_sent_at=old_sent_at,
        expires_at=old_sent_at + dt.timedelta(minutes=15),
        updated_at=None,
    )

    challenge_entity.resend(ttl_minutes=15)

    assert challenge_entity.last_sent_at > old_sent_at
    assert challenge_entity.expires_at == challenge_entity.last_sent_at + dt.timedelta(minutes=15)
    assert challenge_entity.updated_at is not None


def test_ensure_can_attempt_raises_when_expired() -> None:
    """`ensure_can_attempt` бросает на истёкшем challenge'е."""
    challenge_entity = make_challenge(expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1))
    with pytest.raises(ChallengeExpiredError):
        challenge_entity.ensure_can_attempt(max_attempts=5)


def test_ensure_can_attempt_raises_when_used() -> None:
    """`ensure_can_attempt` бросает на использованном challenge'е."""
    challenge_entity = make_challenge(used_at=dt.datetime.now(tz=dt.UTC))
    with pytest.raises(ChallengeExpiredError):
        challenge_entity.ensure_can_attempt(max_attempts=5)


def test_ensure_can_attempt_raises_when_attempts_exhausted() -> None:
    """`ensure_can_attempt` бросает при исчерпании попыток, с секундами до нового кода."""
    challenge_entity = make_challenge(attempts=5)
    with pytest.raises(ChallengeAttemptsExceededError) as exc_info:
        challenge_entity.ensure_can_attempt(max_attempts=5)

    assert exc_info.value.details is not None
    assert "retry_after_seconds" in exc_info.value.details


def test_ensure_can_attempt_ok_when_active_with_attempts_left() -> None:
    """`ensure_can_attempt` молчит, пока challenge активен и есть попытки."""
    challenge_entity = make_challenge(attempts=2)
    challenge_entity.ensure_can_attempt(max_attempts=5)


def test_register_failed_attempt_increments_and_marks_updated() -> None:
    """`register_failed_attempt` инкрементит счётчик и обновляет `updated_at`."""
    challenge_entity = make_challenge(attempts=2, updated_at=None)

    challenge_entity.register_failed_attempt()

    assert challenge_entity.attempts == 3
    assert challenge_entity.updated_at is not None


def test_mark_used_sets_used_at_and_marks_updated() -> None:
    """`mark_used` ставит `used_at` и обновляет `updated_at`."""
    challenge_entity = make_challenge(used_at=None, updated_at=None)

    challenge_entity.mark_used()

    assert challenge_entity.used_at is not None
    assert challenge_entity.updated_at is not None
