from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.config import EmailVerificationConfig
from app.auth.application.schemas.metadata import ClientMetadata
from app.auth.application.services.account import AccountService
from app.auth.application.services.auth import AuthService
from app.auth.application.services.email_verification import EmailVerificationService
from app.auth.application.services.token_issuer import TokenIssuer
from app.auth.exceptions import InvalidRefreshTokenError
from app.auth.infra.clients.internal_users_client import InternalUsersClient
from app.auth.infra.uow import AuthUnitOfWork
from app.auth.presentation.cookies import read_refresh_token_cookie
from app.shared.infra.crypto import (
    DeterministicHasherPort,
    SaltedHasherPort,
    SecretCipherPort,
    get_argon2_salted_hasher,
    get_fernet_secret_cipher,
    get_sha256_deterministic_hasher,
)
from app.shared.infra.jwt.dependency import jwt_service_dependency
from app.shared.infra.jwt.service import JWTService
from app.shared.infra.postgres.dependency import db_session_dependency
from app.shared.infra.procrastinate import TaskBusPort
from app.shared.infra.procrastinate.bus import ProcrastinateTaskBus
from app.shared.schemas.base import BFastAPI
from app.shared.settings import settings
from app.users.application.services.user import UserService
from app.users.presentation.dependencies import user_service_dependency


def client_metadata_dependency(request: Request) -> ClientMetadata:
    return ClientMetadata(
        ip_address=request.client and request.client.host,
        user_agent=request.headers.get("user-agent"),
    )


def auth_uow_dependency(
    session: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> AuthUnitOfWork:
    return AuthUnitOfWork(session=session)


def users_client_dependency(
    user_service: Annotated[UserService, Depends(user_service_dependency)],
) -> InternalUsersClient:
    return InternalUsersClient(user_service=user_service)


def email_verification_config_dependency() -> EmailVerificationConfig:
    return EmailVerificationConfig(
        ttl_minutes=settings.EMAIL_VERIFICATION_TTL_MINUTES,
        max_attempts=settings.EMAIL_VERIFICATION_MAX_ATTEMPTS,
        resend_cooldown_seconds=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
    )


def task_bus_dependency(request: Request) -> TaskBusPort:
    app: BFastAPI = request.app
    return app.registry.get(ProcrastinateTaskBus)


def salted_hasher_dependency() -> SaltedHasherPort:
    """
    Возвращает salt-устойчивый hasher для паролей.

    Stateless singleton на процесс (см. ``get_argon2_salted_hasher``).
    Через override этой dependency тесты подменяют реализацию.

    Scenarios:
        - регистрация и вход: пароль
    """
    return get_argon2_salted_hasher()


def secret_cipher_dependency() -> SecretCipherPort:
    """
    Возвращает шифратор одноразовых кодов.

    Stateless singleton на процесс (см. ``get_fernet_secret_cipher``).

    Scenarios:
        - отправка и ввод кода в диалоге «Подтвердите email»
    """
    return get_fernet_secret_cipher()


def deterministic_hasher_dependency() -> DeterministicHasherPort:
    """
    Возвращает детерминированный hasher для refresh-token lookup'а по индексу.

    Stateless singleton на процесс (см. ``get_sha256_deterministic_hasher``).
    Через override этой dependency тесты подменяют реализацию.

    Scenarios:
        - регистрация и вход: выпуск refresh-токена
        - выход из аккаунта
        - обновление сессии
    """
    return get_sha256_deterministic_hasher()


def optional_refresh_secret_dependency(request: Request) -> str | None:
    """
    Возвращает plaintext-секрет refresh-токена из cookie или ``None``: выход идемпотентен и
    отвечает 204 даже без cookie.

    Scenarios:
        - выход из аккаунта
    """
    return read_refresh_token_cookie(request=request)


def required_refresh_secret_dependency(request: Request) -> str:
    """
    Возвращает plaintext-секрет refresh-токена из cookie или 401.

    Без cookie ротация невозможна, поэтому отсутствие cookie — это уже ошибка
    аутентификации, а не валидации тела.

    Scenarios:
        - обновление сессии

    Raises:
        InvalidRefreshTokenError: Cookie ``refresh_token`` отсутствует
    """
    secret = read_refresh_token_cookie(request=request)
    if secret is None:
        raise InvalidRefreshTokenError()

    return secret


def email_verification_service_dependency(
    *,
    uow: Annotated[AuthUnitOfWork, Depends(auth_uow_dependency)],
    secret_cipher: Annotated[SecretCipherPort, Depends(secret_cipher_dependency)],
    task_bus: Annotated[TaskBusPort, Depends(task_bus_dependency)],
    config: Annotated[EmailVerificationConfig, Depends(email_verification_config_dependency)],
) -> EmailVerificationService:
    return EmailVerificationService(
        uow=uow,
        secret_cipher=secret_cipher,
        task_bus=task_bus,
        config=config,
    )


def account_service_dependency(
    uow: Annotated[AuthUnitOfWork, Depends(auth_uow_dependency)],
) -> AccountService:
    return AccountService(uow=uow)


def token_issuer_dependency(
    *,
    deterministic_hasher: Annotated[DeterministicHasherPort, Depends(deterministic_hasher_dependency)],
    jwt_service: Annotated[JWTService, Depends(jwt_service_dependency)],
) -> TokenIssuer:
    return TokenIssuer(
        deterministic_hasher=deterministic_hasher,
        access_token_issuer=jwt_service,
        refresh_token_ttl_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )


def auth_service_dependency(
    *,
    uow: Annotated[AuthUnitOfWork, Depends(auth_uow_dependency)],
    users_client: Annotated[InternalUsersClient, Depends(users_client_dependency)],
    salted_hasher: Annotated[SaltedHasherPort, Depends(salted_hasher_dependency)],
    token_issuer: Annotated[TokenIssuer, Depends(token_issuer_dependency)],
    email_verification_service: Annotated[EmailVerificationService, Depends(email_verification_service_dependency)],
) -> AuthService:
    return AuthService(
        uow=uow,
        users_client=users_client,
        salted_hasher=salted_hasher,
        token_issuer=token_issuer,
        email_verification_service=email_verification_service,
    )
