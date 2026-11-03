"""
Фикстуры домена auth (unit): сборка application-сервисов на фейках.

Фейки I/O-границы (репозитории, UoW, users-client, hasher'ы, task-bus, email-настройки)
переехали в корневой ``tests/conftest.py`` — они переиспользуются и api-уровнем. Здесь
остаётся только доменно-специфичная проводка сервисов-под-тестом, чтобы тесты не повторяли
её. ``TokenIssuer``, ``JWTService`` и шифратор кодов — реальные (stateless infra, дешёвые и
детерминированные).
"""

import pytest

from app.auth.application.config import EmailVerificationConfig
from app.auth.application.services.account import AccountService
from app.auth.application.services.auth import AuthService
from app.auth.application.services.email_verification import EmailVerificationService
from app.auth.application.services.token_issuer import TokenIssuer
from app.shared.infra.crypto.fernet import FernetSecretCipher
from app.shared.infra.crypto.sha256 import Sha256DeterministicHasher
from app.shared.infra.jwt.service import JWTService
from tests.fakes import (
    FakeAuthUnitOfWork,
    FakeEmailVerificationService,
    FakeSaltedHasher,
    FakeTaskBus,
    FakeUsersClient,
)

_REFRESH_TOKEN_TTL_DAYS = 30


@pytest.fixture
def token_issuer(deterministic_hasher: Sha256DeterministicHasher, jwt_service: JWTService) -> TokenIssuer:
    return TokenIssuer(
        deterministic_hasher=deterministic_hasher,
        access_token_issuer=jwt_service,
        refresh_token_ttl_days=_REFRESH_TOKEN_TTL_DAYS,
    )


@pytest.fixture
def fake_email_verification_service() -> FakeEmailVerificationService:
    return FakeEmailVerificationService()


@pytest.fixture
def auth_service(
    fake_uow: FakeAuthUnitOfWork,
    fake_users_client: FakeUsersClient,
    fake_salted_hasher: FakeSaltedHasher,
    token_issuer: TokenIssuer,
    fake_email_verification_service: FakeEmailVerificationService,
) -> AuthService:
    return AuthService(
        uow=fake_uow,
        users_client=fake_users_client,
        salted_hasher=fake_salted_hasher,
        token_issuer=token_issuer,
        email_verification_service=fake_email_verification_service,
    )


@pytest.fixture
def account_service(fake_uow: FakeAuthUnitOfWork) -> AccountService:
    return AccountService(uow=fake_uow)


@pytest.fixture
def email_verification_service(
    fake_uow: FakeAuthUnitOfWork,
    secret_cipher: FernetSecretCipher,
    fake_task_bus: FakeTaskBus,
    email_verification_config: EmailVerificationConfig,
) -> EmailVerificationService:
    return EmailVerificationService(
        uow=fake_uow,
        secret_cipher=secret_cipher,
        task_bus=fake_task_bus,
        config=email_verification_config,
    )
