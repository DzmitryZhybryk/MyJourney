import datetime as dt
import math
from typing import Final
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

_MAX_ATTEMPTS: Final[int] = 5
_RESEND_COOLDOWN_SECONDS: Final[int] = 60
_TTL_MINUTES: Final[int] = 15


def test_generate_code_is_six_digits() -> None:
    """Код — строка из шести цифр."""
    code = ChallengeEntity.generate_code()
    assert len(code) == 6
    assert code.isdigit()


def test_is_active_unused_live_challenge_is_true() -> None:
    """Неиспользованный и не истёкший challenge активен."""
    challenge_entity = make_challenge(
        used_at=None,
        expires_at=dt.datetime.now(tz=dt.UTC) + dt.timedelta(minutes=10),
    )
    assert challenge_entity.is_active()


def test_is_active_used_challenge_is_false() -> None:
    """Использованный challenge неактивен."""
    challenge_entity = make_challenge(used_at=dt.datetime.now(tz=dt.UTC))
    assert not challenge_entity.is_active()


def test_is_active_expired_challenge_is_false() -> None:
    """Истёкший challenge неактивен."""
    challenge_entity = make_challenge(expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1))
    assert not challenge_entity.is_active()


def test_create_starts_ttl_from_first_send() -> None:
    """Создание отмечает первую отправку и отсчитывает срок от неё."""
    challenge_entity = ChallengeEntity.create(
        user_id=uuid4(),
        challenge_type=ChallengeTypeEnum.EMAIL_VERIFICATION,
        code_ciphertext="ciphertext",
        ttl_minutes=15,
    )

    assert challenge_entity.expires_at == challenge_entity.last_sent_at + dt.timedelta(minutes=15)


def test_is_expired_false_before_and_true_after_expires_at() -> None:
    """До ``expires_at`` код не истёк, после — истёк."""
    now = dt.datetime.now(tz=dt.UTC)

    assert not make_challenge(expires_at=now + dt.timedelta(minutes=1)).is_expired()
    assert make_challenge(expires_at=now - dt.timedelta(seconds=1)).is_expired()


def test_seconds_until_expiry_rounds_up() -> None:
    """Остаток до истечения — целые секунды вверх: 90 с без долей не превращаются в 89."""
    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=90)
    challenge_entity = make_challenge(expires_at=expires_at)

    seconds = challenge_entity.seconds_until_expiry()

    checked_at = dt.datetime.now(tz=dt.UTC)
    assert math.ceil((expires_at - checked_at).total_seconds()) <= seconds <= 90


def test_seconds_until_expiry_expired_code_is_zero() -> None:
    """У истёкшего кода остаток — ноль, а не отрицательное число."""
    challenge_entity = make_challenge(expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=5))

    assert challenge_entity.seconds_until_expiry() == 0


def test_ensure_resend_cooldown_passed_within_cooldown_raises() -> None:
    """С последней отправки прошло меньше паузы → ``ChallengeResendCooldownError``, хотя код создан давно."""
    now = dt.datetime.now(tz=dt.UTC)
    challenge_entity = make_challenge(
        created_at=now - dt.timedelta(minutes=10),
        last_sent_at=now - dt.timedelta(seconds=10),
    )

    with pytest.raises(ChallengeResendCooldownError):
        challenge_entity.ensure_resend_cooldown_passed(_RESEND_COOLDOWN_SECONDS)


def test_ensure_resend_cooldown_passed_after_cooldown_passes() -> None:
    """Пауза с последней отправки прошла — ошибки нет."""
    challenge_entity = make_challenge(last_sent_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=120))

    challenge_entity.ensure_resend_cooldown_passed(_RESEND_COOLDOWN_SECONDS)


def test_ensure_not_exhausted_exhausted_attempts_raises_with_seconds_until_expiry() -> None:
    """Попытки исчерпаны → ``ChallengeAttemptsExceededError`` с секундами до истечения кода в ``details``."""
    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=540)
    challenge_entity = make_challenge(attempts=_MAX_ATTEMPTS, expires_at=expires_at)

    with pytest.raises(ChallengeAttemptsExceededError) as exc_info:
        challenge_entity.ensure_not_exhausted(_MAX_ATTEMPTS)

    checked_at = dt.datetime.now(tz=dt.UTC)
    details = exc_info.value.details
    assert details is not None
    assert details.keys() == {"retry_after_seconds"}
    assert math.ceil((expires_at - checked_at).total_seconds()) <= details["retry_after_seconds"] <= 540


def test_ensure_not_exhausted_attempts_left_passes() -> None:
    """Попытки остались — ошибки нет."""
    challenge_entity = make_challenge(attempts=_MAX_ATTEMPTS - 1)

    challenge_entity.ensure_not_exhausted(_MAX_ATTEMPTS)


def test_resend_moves_last_sent_and_extends_expiry() -> None:
    """Повторная отправка отмечается сейчас, срок продлевается на TTL от неё, ``updated_at`` обновлён."""
    old_sent_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=5)
    challenge_entity = make_challenge(
        last_sent_at=old_sent_at,
        expires_at=old_sent_at + dt.timedelta(minutes=_TTL_MINUTES),
        updated_at=None,
    )

    challenge_entity.resend(_TTL_MINUTES)

    assert challenge_entity.last_sent_at > old_sent_at
    assert challenge_entity.expires_at == challenge_entity.last_sent_at + dt.timedelta(minutes=_TTL_MINUTES)
    assert challenge_entity.updated_at is not None


def test_ensure_can_attempt_expired_challenge_raises() -> None:
    """Истёкший challenge → ``ChallengeExpiredError``."""
    challenge_entity = make_challenge(expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1))
    with pytest.raises(ChallengeExpiredError):
        challenge_entity.ensure_can_attempt(_MAX_ATTEMPTS)


def test_ensure_can_attempt_used_challenge_raises() -> None:
    """Использованный challenge → ``ChallengeExpiredError``."""
    challenge_entity = make_challenge(used_at=dt.datetime.now(tz=dt.UTC))
    with pytest.raises(ChallengeExpiredError):
        challenge_entity.ensure_can_attempt(_MAX_ATTEMPTS)


def test_ensure_can_attempt_exhausted_attempts_raises() -> None:
    """Попытки исчерпаны → ``ChallengeAttemptsExceededError`` с секундами до нового кода."""
    challenge_entity = make_challenge(attempts=_MAX_ATTEMPTS)
    with pytest.raises(ChallengeAttemptsExceededError) as exc_info:
        challenge_entity.ensure_can_attempt(_MAX_ATTEMPTS)

    assert exc_info.value.details is not None
    assert "retry_after_seconds" in exc_info.value.details


def test_ensure_can_attempt_active_with_attempts_left_passes() -> None:
    """Активный challenge с оставшимися попытками — ошибки нет."""
    challenge_entity = make_challenge(attempts=2)
    challenge_entity.ensure_can_attempt(_MAX_ATTEMPTS)


def test_register_failed_attempt_increments_and_marks_updated() -> None:
    """Неудачная попытка увеличивает счётчик и обновляет ``updated_at``."""
    challenge_entity = make_challenge(attempts=2, updated_at=None)

    challenge_entity.register_failed_attempt()

    assert challenge_entity.attempts == 3
    assert challenge_entity.updated_at is not None


def test_mark_used_sets_used_at_and_marks_updated() -> None:
    """Ставит ``used_at`` и обновляет ``updated_at``."""
    challenge_entity = make_challenge(used_at=None, updated_at=None)

    challenge_entity.mark_used()

    assert challenge_entity.used_at is not None
    assert challenge_entity.updated_at is not None
