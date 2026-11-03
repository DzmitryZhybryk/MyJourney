import datetime as dt
import math
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
from app.shared.infra.crypto.fernet import FernetSecretCipher
from tests.builders import make_challenge, make_user_credentials
from tests.fakes import (
    FakeAuthUnitOfWork,
    FakeChallengeRepository,
    FakeTaskBus,
    FakeUserCredentialsRepository,
)

_VERIFICATION_CODE_LENGTH = 6


# --- request_email_verification --------------------------------------------


async def test_request_creates_challenge_and_defers_email_atomically(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
    secret_cipher: FernetSecretCipher,
) -> None:
    """request: создаёт challenge, кладёт шифротекст кода (код уходит в письмо), defer'ит в сессии UoW, коммитит."""
    user_credentials_entity = make_user_credentials(email="neo@example.com", email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)

    await email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)

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
    code = secret_cipher.decrypt(ciphertext=challenge_entity.code_ciphertext)
    assert code.isdigit()
    assert len(code) == _VERIFICATION_CODE_LENGTH

    assert fake_task_bus.bound_session is fake_uow.session
    fake_uow.commit_mock.assert_awaited_once()


async def test_request_raises_when_user_not_found(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
) -> None:
    """request: нет учётной записи → AccountNotFoundError, без challenge, defer'а и коммита."""
    with pytest.raises(AccountNotFoundError):
        await email_verification_service.request_email_verification(user_id=uuid4())

    assert fake_challenge_repository.challenges == []
    assert fake_task_bus.bound.deferred == []
    fake_uow.commit_mock.assert_not_awaited()


async def test_request_raises_when_email_already_verified(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
) -> None:
    """request: email уже подтверждён → EmailAlreadyVerifiedError, без challenge и коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)

    with pytest.raises(EmailAlreadyVerifiedError):
        await email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)

    assert fake_challenge_repository.challenges == []
    fake_uow.commit_mock.assert_not_awaited()


async def test_request_raises_when_resend_cooldown_active(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
) -> None:
    """request: активный challenge свежее cooldown'а → ChallengeResendCooldownError, без нового challenge и коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    existing = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        last_sent_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=10),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=existing)

    with pytest.raises(ChallengeResendCooldownError):
        await email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)

    assert len(fake_challenge_repository.challenges) == 1
    assert existing.used_at is None
    fake_uow.commit_mock.assert_not_awaited()


async def test_request_resends_same_code_and_extends_expiry_when_code_live(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
    secret_cipher: FernetSecretCipher,
) -> None:
    """request: живой код после cooldown'а уходит тот же, срок продлевается, нового challenge'а нет."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    now = dt.datetime.now(tz=dt.UTC)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        code_ciphertext=secret_cipher.encrypt(secret="123456"),
        last_sent_at=now - dt.timedelta(seconds=120),
        expires_at=now + dt.timedelta(minutes=13),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=previous)

    await email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)

    assert fake_challenge_repository.challenges == [previous]
    assert previous.used_at is None
    assert previous.expires_at == previous.last_sent_at + dt.timedelta(minutes=15)
    deferred = fake_task_bus.bound.deferred[0]
    assert secret_cipher.decrypt(ciphertext=deferred.kwargs["code_ciphertext"]) == "123456"
    assert deferred.kwargs["expires_at"] == previous.expires_at.isoformat()
    fake_uow.commit_mock.assert_awaited_once()


@pytest.mark.parametrize("attempts", [0, 5])
async def test_request_replaces_expired_challenge_with_new_code(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
    attempts: int,
) -> None:
    """request: истёкший код (с попытками или без) гасится, выдаётся и уходит в письмо новый."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    now = dt.datetime.now(tz=dt.UTC)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=attempts,
        last_sent_at=now - dt.timedelta(minutes=20),
        expires_at=now - dt.timedelta(minutes=5),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=previous)

    await email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)

    assert previous.used_at is not None
    active = [c for c in fake_challenge_repository.challenges if c.used_at is None]
    assert len(active) == 1
    assert fake_task_bus.bound.deferred[0].kwargs["code_ciphertext"] == active[0].code_ciphertext
    fake_uow.commit_mock.assert_awaited_once()


async def test_request_raises_attempts_exceeded_when_live_code_exhausted(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    fake_task_bus: FakeTaskBus,
) -> None:
    """request: живой код исчерпан → 429 с секундами до его истечения; без письма, продления и коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    now = dt.datetime.now(tz=dt.UTC)
    expires_at = now + dt.timedelta(seconds=300)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=5,
        last_sent_at=now - dt.timedelta(seconds=120),
        expires_at=expires_at,
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=previous)

    with pytest.raises(ChallengeAttemptsExceededError) as exc_info:
        await email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)

    checked_at = dt.datetime.now(tz=dt.UTC)
    details = exc_info.value.details
    assert details is not None
    assert details.keys() == {"retry_after_seconds"}
    assert math.ceil((expires_at - checked_at).total_seconds()) <= details["retry_after_seconds"] <= 300
    assert previous.expires_at == expires_at
    assert fake_task_bus.bound.deferred == []
    fake_uow.commit_mock.assert_not_awaited()


async def test_request_reports_exhausted_code_before_cooldown(
    email_verification_service: EmailVerificationService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
) -> None:
    """request: исчерпанный код внутри cooldown'а → «попытки исчерпаны» со временем, а не «подождите»."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    previous = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=5,
        last_sent_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=10),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=previous)

    with pytest.raises(ChallengeAttemptsExceededError):
        await email_verification_service.request_email_verification(user_id=user_credentials_entity.user_id)


# --- verify_email -----------------------------------------------------------


async def test_verify_marks_email_verified_on_correct_code(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """verify: верный код помечает email подтверждённым, закрывает challenge, коммитит."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        code_ciphertext=secret_cipher.encrypt(secret="123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=challenge_entity)

    await email_verification_service.verify_email(
        user_id=user_credentials_entity.user_id,
        command=VerifyEmailCommand(code=SecretStr("123456")),
    )

    assert user_credentials_entity.is_email_verified
    assert challenge_entity.used_at is not None
    fake_uow.commit_mock.assert_awaited_once()


async def test_verify_increments_attempts_and_raises_on_wrong_code(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """verify: неверный код инкрементит счётчик попыток, коммитит инкремент и бросает VerificationCodeInvalidError."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=0,
        code_ciphertext=secret_cipher.encrypt(secret="123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=challenge_entity)

    with pytest.raises(VerificationCodeInvalidError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("000000")),
        )

    assert challenge_entity.attempts == 1
    assert not user_credentials_entity.is_email_verified
    fake_uow.commit_mock.assert_awaited_once()


async def test_verify_raises_when_user_not_found(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
) -> None:
    """verify: нет учётной записи → AccountNotFoundError, без коммита."""
    with pytest.raises(AccountNotFoundError):
        await email_verification_service.verify_email(
            user_id=uuid4(), command=VerifyEmailCommand(code=SecretStr("123456"))
        )

    fake_uow.commit_mock.assert_not_awaited()


async def test_verify_raises_when_email_already_verified(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
) -> None:
    """verify: email уже подтверждён → EmailAlreadyVerifiedError, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=dt.datetime.now(tz=dt.UTC))
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)

    with pytest.raises(EmailAlreadyVerifiedError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("123456")),
        )

    fake_uow.commit_mock.assert_not_awaited()


async def test_verify_raises_when_no_active_challenge(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
) -> None:
    """verify: у пользователя нет активного challenge'а → ChallengeNotFoundError, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)

    with pytest.raises(ChallengeNotFoundError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("123456")),
        )

    fake_uow.commit_mock.assert_not_awaited()


async def test_verify_raises_when_attempts_exhausted(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """verify: лимит исчерпан → 429 с секундами до нового кода ещё до сверки кода, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=420)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        attempts=5,
        code_ciphertext=secret_cipher.encrypt(secret="123456"),
        expires_at=expires_at,
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=challenge_entity)

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
    fake_uow.commit_mock.assert_not_awaited()


async def test_verify_non_ascii_digits_count_as_wrong_code(
    email_verification_service: EmailVerificationService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """verify: не-ASCII цифры — обычный неверный код (попытка списана), а не падение сравнения."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        code_ciphertext=secret_cipher.encrypt(secret="123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=challenge_entity)

    with pytest.raises(VerificationCodeInvalidError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("١٢٣٤٥٦")),
        )

    assert challenge_entity.attempts == 1


async def test_verify_raises_when_challenge_expired(
    email_verification_service: EmailVerificationService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
) -> None:
    """verify: срок действия challenge'а истёк → ChallengeExpiredError, без коммита."""
    user_credentials_entity = make_user_credentials(email_verified_at=None)
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    challenge_entity = make_challenge(
        user_id=user_credentials_entity.user_id,
        used_at=None,
        expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1),
        code_ciphertext=secret_cipher.encrypt(secret="123456"),
    )
    await fake_challenge_repository.insert_challenge(challenge_entity=challenge_entity)

    with pytest.raises(ChallengeExpiredError):
        await email_verification_service.verify_email(
            user_id=user_credentials_entity.user_id,
            command=VerifyEmailCommand(code=SecretStr("123456")),
        )

    fake_uow.commit_mock.assert_not_awaited()
