"""
api-тесты email-роутов (send-verification / verify) через ASGI без реальной БД.

Эти роуты защищены Bearer'ом: ``current_user_id_dependency`` — настоящий, токен выпускаем
``mint_access_token`` тем же ``get_jwt_service()``, которым приложение его и декодит. I/O
(UoW/репо, task-bus) — фейки; шифратор кодов настоящий, с ключом из settings, как у приложения.
Пиннят статусы и машинные ``code`` всей матрицы доменных ошибок верификации.
"""

import datetime as dt
import math
from collections.abc import Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.auth.application.config import EmailVerificationConfig
from app.shared.infra.crypto.fernet import FernetSecretCipher
from tests.builders import make_challenge, make_user_credentials
from tests.fakes import (
    FakeChallengeRepository,
    FakeTaskBus,
    FakeUserCredentialsRepository,
)

_SEND_VERIFICATION_URL = "/v1/auth/email/send-verification/"
_VERIFY_URL = "/v1/auth/email/verify/"


# --- send-verification -------------------------------------------------------


async def test_send_verification_returns_202_and_defers_email(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_task_bus: FakeTaskBus,
    mint_access_token: Callable[..., str],
) -> None:
    """send-verification для неподтверждённой учётки → 202, таска на письмо поставлена в очередь."""
    user_credentials_entity = make_user_credentials()
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(_SEND_VERIFICATION_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 202
    assert len(fake_task_bus.bound.deferred) == 1


async def test_send_verification_without_bearer_returns_401(client: AsyncClient) -> None:
    """send-verification без Authorization → 401 auth.invalid_access_token."""
    response = await client.post(_SEND_VERIFICATION_URL)

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_send_verification_malformed_bearer_returns_401(client: AsyncClient) -> None:
    """send-verification с битым Bearer-токеном → 401 auth.invalid_access_token."""
    response = await client.post(_SEND_VERIFICATION_URL, headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_send_verification_unknown_user_returns_401(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """send-verification с токеном без учётки в БД → 401 auth.account_not_found."""
    token = mint_access_token(user_id=uuid4())

    response = await client.post(_SEND_VERIFICATION_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["code"] == "auth.account_not_found"


async def test_send_verification_already_verified_returns_409(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    mint_access_token: Callable[..., str],
    past: dt.datetime,
) -> None:
    """send-verification для уже подтверждённого email → 409 auth.email_already_verified."""
    user_credentials_entity = make_user_credentials(email_verified_at=past)
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(_SEND_VERIFICATION_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 409
    assert response.json()["code"] == "auth.email_already_verified"


async def test_send_verification_within_cooldown_returns_429(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """send-verification при свежем активном challenge → 429 auth.challenge_resend_cooldown."""
    user_credentials_entity = make_user_credentials()
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    fake_challenge_repository.challenges.append(make_challenge(user_id=user_credentials_entity.user_id))
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(_SEND_VERIFICATION_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 429
    assert response.json()["code"] == "auth.challenge_resend_cooldown"


async def test_send_verification_exhausted_live_code_returns_429_with_retry_after(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    email_verification_config: EmailVerificationConfig,
    mint_access_token: Callable[..., str],
) -> None:
    """send-verification при исчерпанном живом коде → 429 auth.challenge_attempts_exceeded с секундами в details."""
    user_credentials_entity = make_user_credentials()
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=300)
    fake_challenge_repository.challenges.append(
        make_challenge(
            user_id=user_credentials_entity.user_id,
            attempts=email_verification_config.max_attempts,
            expires_at=expires_at,
        )
    )
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(_SEND_VERIFICATION_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "auth.challenge_attempts_exceeded"
    checked_at = dt.datetime.now(tz=dt.UTC)
    assert body["details"].keys() == {"retry_after_seconds"}
    seconds = body["details"]["retry_after_seconds"]
    assert math.ceil((expires_at - checked_at).total_seconds()) <= seconds <= 300


# --- verify ------------------------------------------------------------------


@pytest.mark.parametrize("submitted_code", ["123456", " 123456 "])
async def test_verify_valid_code_returns_204_and_marks_verified(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
    mint_access_token: Callable[..., str],
    submitted_code: str,
) -> None:
    """verify с верным кодом (в т.ч. с пробелами по краям) → 204, email подтверждён, challenge использован."""
    user_credentials_entity = make_user_credentials()
    challenge = make_challenge(
        user_id=user_credentials_entity.user_id, code_ciphertext=secret_cipher.encrypt(secret="123456")
    )
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    fake_challenge_repository.challenges.append(challenge)
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": submitted_code},
    )

    assert response.status_code == 204
    assert user_credentials_entity.is_email_verified
    assert challenge.used_at is not None


@pytest.mark.parametrize("wrong_code", ["000000", "١٢٣٤٥٦"])
async def test_verify_wrong_code_returns_400_and_increments_attempts(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
    mint_access_token: Callable[..., str],
    wrong_code: str,
) -> None:
    """verify с неверным кодом (в т.ч. не-ASCII цифрами) → 400 auth.verification_code_invalid, попытка +1."""
    user_credentials_entity = make_user_credentials()
    challenge = make_challenge(
        user_id=user_credentials_entity.user_id, code_ciphertext=secret_cipher.encrypt(secret="123456")
    )
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    fake_challenge_repository.challenges.append(challenge)
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": wrong_code},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "auth.verification_code_invalid"
    assert body["details"] == {"field": "code"}
    assert challenge.attempts == 1


async def test_verify_unknown_user_returns_401(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """verify с токеном без учётки в БД → 401 auth.account_not_found."""
    token = mint_access_token(user_id=uuid4())

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "123456"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "auth.account_not_found"


async def test_verify_no_active_challenge_returns_404(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """verify без активного challenge → 404 auth.challenge_not_found."""
    user_credentials_entity = make_user_credentials()
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "123456"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "auth.challenge_not_found"


async def test_verify_already_verified_returns_409(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    mint_access_token: Callable[..., str],
    past: dt.datetime,
) -> None:
    """verify для уже подтверждённого email → 409 auth.email_already_verified."""
    user_credentials_entity = make_user_credentials(email_verified_at=past)
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "123456"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "auth.email_already_verified"


async def test_verify_expired_challenge_returns_410(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
    mint_access_token: Callable[..., str],
    past: dt.datetime,
) -> None:
    """verify по истёкшему challenge → 410 auth.challenge_expired."""
    code = "123456"
    user_credentials_entity = make_user_credentials()
    challenge = make_challenge(
        user_id=user_credentials_entity.user_id,
        code_ciphertext=secret_cipher.encrypt(secret=code),
        expires_at=past,
    )
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    fake_challenge_repository.challenges.append(challenge)
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": code},
    )

    assert response.status_code == 410
    assert response.json()["code"] == "auth.challenge_expired"


async def test_verify_attempts_exceeded_returns_429(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_challenge_repository: FakeChallengeRepository,
    secret_cipher: FernetSecretCipher,
    email_verification_config: EmailVerificationConfig,
    mint_access_token: Callable[..., str],
) -> None:
    """verify при выбранном лимите попыток → 429 auth.challenge_attempts_exceeded с секундами в details."""
    code = "123456"
    user_credentials_entity = make_user_credentials()
    expires_at = dt.datetime.now(tz=dt.UTC) + dt.timedelta(seconds=420)
    challenge = make_challenge(
        user_id=user_credentials_entity.user_id,
        code_ciphertext=secret_cipher.encrypt(secret=code),
        attempts=email_verification_config.max_attempts,
        expires_at=expires_at,
    )
    fake_user_credentials_repository.by_user_id[user_credentials_entity.user_id] = user_credentials_entity
    fake_challenge_repository.challenges.append(challenge)
    token = mint_access_token(user_id=user_credentials_entity.user_id)

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": code},
    )

    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "auth.challenge_attempts_exceeded"
    checked_at = dt.datetime.now(tz=dt.UTC)
    assert body["details"].keys() == {"retry_after_seconds"}
    seconds = body["details"]["retry_after_seconds"]
    assert math.ceil((expires_at - checked_at).total_seconds()) <= seconds <= 420


async def test_verify_malformed_code_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """verify с кодом не из 6 цифр → 422 validation_error (валидный Bearer, ошибка в теле)."""
    token = mint_access_token(user_id=uuid4())

    response = await client.post(
        _VERIFY_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "abc"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
