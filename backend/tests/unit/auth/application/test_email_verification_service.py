import datetime as dt
import math
from typing import Final
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.auth.application.ports.tasks import SEND_VERIFICATION_EMAIL_TASK
from app.auth.application.schemas.commands import VerifyEmailCommand
from app.auth.application.services.email_verification import EmailVerificationService
from app.auth.domain.enums import ChallengeTypeEnum
from app.auth.exceptions import (
    AccountNotFoundError,
    ChallengeAttemptsExceededError,
    ChallengeExpiredError,
    ChallengeNotFoundError,
    ChallengeResendCooldownError,
    EmailAlreadyVerifiedError,
    VerificationCodeInvalidError,
)
from app.shared.events import AccountChangedEvent
from app.shared.infra.crypto.fernet import FernetSecretCipher
from tests.builders import make_challenge, make_user_credentials
from tests.fakes import (
    FakeAuthUnitOfWork,
    FakeChallengeRepository,
    FakeEventPublisher,
    FakeTaskBus,
    FakeUserCredentialsRepository,
)

_VERIFICATION_CODE_LENGTH: Final[int] = 6


# --- request_email_verification --------------------------------------------


async def test_request_email_verification_creates_challenge_and_defers_email_atomically(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Challenge с шифротекстом кода и задача письма с самим кодом ставятся в сессии UoW одним коммитом."""
    user_credentials_entity = make_user_credentials(email="neo@example.com", email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)

    await email_verification_service.request_email_verification(user_credentials_entity.user_id)

    assert len(fake_challenge_repository.challenges) == 1
    challenge_entity = fake_challenge_repository.challenges[0]
    assert challenge_entity.user_id == user_credentials_entity.user_id
    assert challenge_entity.challenge_type is ChallengeTypeEnum.EMAIL_VERIFICATION

    assert len(fake_task_bus.bound.deferred) == 1
    deferred = fake_task_bus.bound.deferred[0]
    assert deferred.task_name == SEND_VERIFICATION_EMAIL_TASK
    assert deferred.lock == f"email_verification:user:{user_credentials_entity.user_id}"
    assert deferred.kwargs["email"] == "neo@example.com"
    assert deferred.kwargs["user_id"] == str(user_credentials_entity.user_id)

    assert deferred.kwargs["code_ciphertext"] == challenge_entity.code_ciphertext
    assert deferred.kwargs["expires_at"] == challenge_entity.expires_at.isoformat()
    code = secret_cipher.decrypt(challenge_entity.code_ciphertext)
    assert code.isdigit()
    assert len(code) == _VERIFICATION_CODE_LENGTH

    assert fake_task_bus.bound_session is fake_auth_uow.session
    fake_auth_uow.commit_mock.assert_awaited_once()


async def test_request_email_verification_unknown_user_raises_account_not_found(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
) -> None:
    """Нет учётной записи → ``AccountNotFoundError``; ни challenge, ни письма, ни коммита."""
    with pytest.raises(AccountNotFoundError):
        await email_verification_service.request_email_verification(uuid4())

    assert fake_challenge_repository.challenges == []
    assert fake_task_bus.bound.deferred == []
    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_request_email_verification_verified_email_raises_email_already_verified(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
) -> None:
    """Email уже подтверждён → ``EmailAlreadyVerifiedError``; ни challenge, ни коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)

    with pytest.raises(EmailAlreadyVerifiedError):
        await email_verification_service.request_email_verification(user_credentials_entity.user_id)

    assert fake_challenge_repository.challenges == []
    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_request_email_verification_within_cooldown_raises_resend_cooldown(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
) -> None:
    """Challenge свежее паузы между отправками → ``ChallengeResendCooldownError``; ни нового challenge, ни коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    existing = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        last_sent_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=10),
    )
    await fake_challenge_repository.insert_challenge(existing)

    with pytest.raises(ChallengeResendCooldownError):
        await email_verification_service.request_email_verification(user_credentials_entity.user_id)

    assert len(fake_challenge_repository.challenges) == 1
    assert existing.used_at is None
    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_request_email_verification_live_code_resends_it_and_extends_expiry(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Живой код после паузы уходит тот же, срок продлевается, нового challenge нет."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    now = dt.datetime.now(tz=dt.UTC)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        code_ciphertext=secret_cipher.encrypt("123456"),
        last_sent_at=now - dt.timedelta(seconds=120),
        expires_at=now + dt.timedelta(minutes=13),
    )
    await fake_challenge_repository.insert_challenge(previous)

    await email_verification_service.request_email_verification(user_credentials_entity.user_id)

    assert fake_challenge_repository.challenges == [previous]
    assert previous.used_at is None
    assert previous.expires_at == previous.last_sent_at + dt.timedelta(minutes=15)
    deferred = fake_task_bus.bound.deferred[0]
    assert secret_cipher.decrypt(deferred.kwargs["code_ciphertext"]) == "123456"
    assert deferred.kwargs["expires_at"] == previous.expires_at.isoformat()
    fake_auth_uow.commit_mock.assert_awaited_once()


@pytest.mark.parametrize("attempts", [0, 5])
async def test_request_email_verification_expired_code_issues_new_code(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
    attempts: int,
) -> None:
    """Истёкший код (с попытками или без) гасится, в письмо уходит новый."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    now = dt.datetime.now(tz=dt.UTC)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=attempts,
        last_sent_at=now - dt.timedelta(minutes=20),
        expires_at=now - dt.timedelta(minutes=5),
    )
    await fake_challenge_repository.insert_challenge(previous)

    await email_verification_service.request_email_verification(user_credentials_entity.user_id)

    assert previous.used_at is not None
    active = [c for c in fake_challenge_repository.challenges if c.used_at is None]
    assert len(active) == 1
    assert fake_task_bus.bound.deferred[0].kwargs["code_ciphertext"] == active[0].code_ciphertext
    fake_auth_uow.commit_mock.assert_awaited_once()


async def test_request_email_verification_exhausted_live_code_raises_attempts_exceeded(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
) -> None:
    """Живой код исчерпан → ``ChallengeAttemptsExceededError`` с секундами до его истечения; ни письма, ни коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    now = dt.datetime.now(tz=dt.UTC)
    expires_at = now + dt.timedelta(seconds=300)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=5,
        last_sent_at=now - dt.timedelta(seconds=120),
        expires_at=expires_at,
    )
    await fake_challenge_repository.insert_challenge(previous)

    with pytest.raises(ChallengeAttemptsExceededError) as exc_info:
        await email_verification_service.request_email_verification(user_credentials_entity.user_id)

    checked_at = dt.datetime.now(tz=dt.UTC)
    details = exc_info.value.details
    assert details is not None
    assert details.keys() == {"retry_after_seconds"}
    assert math.ceil((expires_at - checked_at).total_seconds()) <= details["retry_after_seconds"] <= 300
    assert previous.expires_at == expires_at
    assert fake_task_bus.bound.deferred == []
    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_request_email_verification_exhausted_code_within_cooldown_raises_attempts_exceeded(
    email_verification_service: EmailVerificationService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
) -> None:
    """Исчерпанный код внутри паузы → «попытки исчерпаны» со временем, а не «подождите»."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=5,
        last_sent_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=10),
    )
    await fake_challenge_repository.insert_challenge(previous)

    with pytest.raises(ChallengeAttemptsExceededError):
        await email_verification_service.request_email_verification(user_credentials_entity.user_id)


# --- verify_email -----------------------------------------------------------


async def test_verify_email_correct_code_marks_email_verified(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Верный код подтверждает email и закрывает challenge, коммит."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        code_ciphertext=secret_cipher.encrypt("123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity)

    await email_verification_service.verify_email(
        user_id=user_credentials_entity.user_id,
        command=VerifyEmailCommand(code=SecretStr("123456")),
    )

    assert user_credentials_entity.is_email_verified
    assert challenge_entity.used_at is not None
    fake_auth_uow.commit_mock.assert_awaited_once()


async def test_verify_email_publishes_account_changed_with_verified_state_and_next_version(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_event_publisher: FakeEventPublisher,
    secret_cipher: FernetSecretCipher,
) -> None:
    """В сессии UoW публикуется снимок учётной записи с датой подтверждения и версией на единицу выше."""
    user_credentials_entity = make_user_credentials(email_verified_at=None, version=2)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    await fake_challenge_repository.insert_challenge(
        make_challenge(
            user_id=user_credentials_entity.user_id,
            used_at=None,
            code_ciphertext=secret_cipher.encrypt("123456"),
        ),
    )

    await email_verification_service.verify_email(
        user_id=user_credentials_entity.user_id,
        command=VerifyEmailCommand(code=SecretStr("123456")),
    )

    assert fake_event_publisher.bound_session is fake_auth_uow.session
    assert fake_event_publisher.bound.published == [
        AccountChangedEvent(
            user_id=user_credentials_entity.user_id,
            email=user_credentials_entity.email,
            username=user_credentials_entity.username,
            role=user_credentials_entity.role.value,
            plan=user_credentials_entity.plan.value,
            email_verified_at=user_credentials_entity.email_verified_at,
            registered_at=user_credentials_entity.created_at,
            deleted_at=None,
            version=3,
        ),
    ]


async def test_verify_email_wrong_code_publishes_nothing(
    email_verification_service: EmailVerificationService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_event_publisher: FakeEventPublisher,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Неверный код не меняет учётную запись, поэтому событие не публикуется."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    await fake_challenge_repository.insert_challenge(
        make_challenge(
            user_id=user_credentials_entity.user_id,
            used_at=None,
            code_ciphertext=secret_cipher.encrypt("123456"),
        ),
    )

    with pytest.raises(VerificationCodeInvalidError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("000000")),
        )

    assert fake_event_publisher.bound.published == []


async def test_verify_email_wrong_code_counts_attempt_and_raises_code_invalid(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Неверный код: попытка списана и закоммичена, ``VerificationCodeInvalidError``."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=0,
        code_ciphertext=secret_cipher.encrypt("123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity)

    with pytest.raises(VerificationCodeInvalidError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("000000")),
        )

    assert challenge_entity.attempts == 1
    assert not user_credentials_entity.is_email_verified
    fake_auth_uow.commit_mock.assert_awaited_once()


async def test_verify_email_unknown_user_raises_account_not_found(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
) -> None:
    """Нет учётной записи → ``AccountNotFoundError``, без коммита."""
    with pytest.raises(AccountNotFoundError):
        await email_verification_service.verify_email(
            user_id=uuid4(), command=VerifyEmailCommand(code=SecretStr("123456"))
        )

    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_verify_email_verified_email_raises_email_already_verified(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
) -> None:
    """Email уже подтверждён → ``EmailAlreadyVerifiedError``, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)

    with pytest.raises(EmailAlreadyVerifiedError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("123456")),
        )

    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_verify_email_without_active_challenge_raises_challenge_not_found(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
) -> None:
    """Активного challenge нет → ``ChallengeNotFoundError``, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)

    with pytest.raises(ChallengeNotFoundError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("123456")),
        )

    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_verify_email_exhausted_attempts_raises_attempts_exceeded(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Лимит исчерпан → ``ChallengeAttemptsExceededError`` с секундами до нового кода ещё до сверки, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=420)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=5,
        code_ciphertext=secret_cipher.encrypt("123456"),
        expires_at=expires_at,
    )
    await fake_challenge_repository.insert_challenge(challenge_entity)

    with pytest.raises(ChallengeAttemptsExceededError) as exc_info:
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("123456")),
        )

    checked_at = dt.datetime.now(tz=dt.UTC)
    details = exc_info.value.details
    assert details is not None
    assert details.keys() == {"retry_after_seconds"}
    assert math.ceil((expires_at - checked_at).total_seconds()) <= details["retry_after_seconds"] <= 420
    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_verify_email_non_ascii_digits_count_as_wrong_code(
    email_verification_service: EmailVerificationService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Не-ASCII цифры — обычный неверный код (попытка списана), а не падение сравнения."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        code_ciphertext=secret_cipher.encrypt("123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity)

    with pytest.raises(VerificationCodeInvalidError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("١٢٣٤٥٦")),
        )

    assert challenge_entity.attempts == 1


async def test_verify_email_expired_challenge_raises_challenge_expired(
    email_verification_service: EmailVerificationService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """Срок challenge истёк → ``ChallengeExpiredError``, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1),
        code_ciphertext=secret_cipher.encrypt("123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity)

    with pytest.raises(ChallengeExpiredError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("123456")),
        )

    fake_auth_uow.commit_mock.assert_not_awaited()
