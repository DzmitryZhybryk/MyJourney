import datetime as dt
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.auth.application.schemas.commands import LoginCommand, RegistrationCommand
from app.auth.application.schemas.metadata import ClientMetadata
from app.auth.application.services.auth import AuthService
from app.auth.application.services.token_issuer import TokenIssuer
from app.auth.exceptions import (
    EmailAlreadyExistError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UsernameAlreadyExistError,
)
from app.shared.events import AccountChangedEvent
from app.shared.infra.crypto.sha256 import Sha256DeterministicHasher
from tests.builders import make_password, make_refresh_token, make_user_credentials
from tests.fakes import (
    FakeAuthUnitOfWork,
    FakeEmailVerificationService,
    FakeEventPublisher,
    FakeRefreshTokenRepository,
    FakeSaltedHasher,
    FakeUserCredentialsRepository,
    FakeUsersClient,
)

_CLIENT_METADATA = ClientMetadata(ip_address="1.2.3.4", user_agent="UA")


# --- register ---------------------------------------------------------------


async def test_register_persists_credentials_calls_users_and_requests_verification(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_users_client: FakeUsersClient,
    fake_email_verification_service: FakeEmailVerificationService,
    fake_salted_hasher: FakeSaltedHasher,
    deterministic_hasher: Sha256DeterministicHasher,
) -> None:
    """Хеш пароля, учётка, профиль в users, refresh — одним коммитом, затем запрос подтверждения email."""
    command = RegistrationCommand(
        username="neo",
        email="neo@example.com",
        password=SecretStr("pw"),
        marketing_emails_consent=True,
    )

    pair = await auth_service.register(command=command, client_metadata=_CLIENT_METADATA)

    assert len(fake_user_credentials_repository.by_user_id) == 1
    stored = next(iter(fake_user_credentials_repository.by_user_id.values()))
    assert stored.email == "neo@example.com"
    assert stored.username == "neo"
    assert stored.password.hash == fake_salted_hasher.hash("pw")

    assert len(fake_users_client.created) == 1
    created = fake_users_client.created[0]
    assert created.user_id == stored.user_id
    assert created.display_name == "neo"
    assert created.marketing_emails_consent is True
    assert created.terms_accepted_at == stored.created_at

    stored_hash = deterministic_hasher.digest(pair.refresh_token.secret.get_secret_value())
    assert stored_hash in fake_refresh_token_repository.by_hash

    fake_auth_uow.commit_mock.assert_awaited_once()
    assert fake_email_verification_service.requested_user_ids == [stored.user_id]


async def test_register_publishes_account_changed_with_first_version(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_event_publisher: FakeEventPublisher,
) -> None:
    """В сессии UoW публикуется снимок новой учётной записи с версией 1."""
    command = RegistrationCommand(
        username="neo",
        email="neo@example.com",
        password=SecretStr("pw"),
        marketing_emails_consent=False,
    )

    await auth_service.register(command=command, client_metadata=_CLIENT_METADATA)

    stored = next(iter(fake_user_credentials_repository.by_user_id.values()))
    assert fake_event_publisher.bound_session is fake_auth_uow.session
    assert fake_event_publisher.bound.published == [
        AccountChangedEvent(
            user_id=stored.user_id,
            email="neo@example.com",
            username="neo",
            role="user",
            plan="free",
            email_verified_at=None,
            registered_at=stored.created_at,
            deleted_at=None,
            version=1,
        ),
    ]


@pytest.mark.parametrize("email", ["neo@example.com", "NEO@Example.com"])
async def test_register_taken_email_raises_email_already_exists(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_users_client: FakeUsersClient,
    email: str,
) -> None:
    """Занятый email (в любом регистре) → ``EmailAlreadyExistError``; ни новой записи, ни вызова users, ни коммита."""
    await fake_user_credentials_repository.insert_user_credentials(
        make_user_credentials(email="neo@example.com", username="existing"),
    )
    command = RegistrationCommand(
        username="neo",
        email=email,
        password=SecretStr("pw"),
        marketing_emails_consent=False,
    )

    with pytest.raises(EmailAlreadyExistError):
        await auth_service.register(command=command, client_metadata=_CLIENT_METADATA)

    assert len(fake_user_credentials_repository.by_user_id) == 1
    assert fake_users_client.created == []
    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_register_users_creation_failure_does_not_commit(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_users_client: FakeUsersClient,
    fake_email_verification_service: FakeEmailVerificationService,
) -> None:
    """Сбой создания профиля в users пробрасывается; ни коммита, ни запроса подтверждения."""
    fake_users_client.error = RuntimeError("users service down")
    command = RegistrationCommand(
        username="neo",
        email="neo@example.com",
        password=SecretStr("pw"),
        marketing_emails_consent=True,
    )

    with pytest.raises(RuntimeError, match="users service down"):
        await auth_service.register(command=command, client_metadata=_CLIENT_METADATA)

    fake_auth_uow.commit_mock.assert_not_awaited()
    assert fake_email_verification_service.requested_user_ids == []


@pytest.mark.parametrize("username", ["neo", "NeO"])
async def test_register_taken_username_raises_username_already_exists(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    username: str,
) -> None:
    """Свободный email, но занятый username (в любом регистре) → ``UsernameAlreadyExistError``, без коммита."""
    await fake_user_credentials_repository.insert_user_credentials(
        make_user_credentials(email="taken@example.com", username="neo"),
    )
    command = RegistrationCommand(
        username=username,
        email="new@example.com",
        password=SecretStr("pw"),
        marketing_emails_consent=False,
    )

    with pytest.raises(UsernameAlreadyExistError):
        await auth_service.register(command=command, client_metadata=_CLIENT_METADATA)

    fake_auth_uow.commit_mock.assert_not_awaited()


# --- login ------------------------------------------------------------------


@pytest.mark.parametrize("login", ["neo@example.com", "NEO@Example.COM"])
async def test_login_with_email_returns_token_pair(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
    login: str,
) -> None:
    """Вход по email (в любом регистре) с верным паролем выдаёт пару токенов и сохраняет refresh."""
    await fake_user_credentials_repository.insert_user_credentials(
        make_user_credentials(
            email="neo@example.com",
            username="neo",
            password=make_password(fake_salted_hasher.hash("pw")),
        ),
    )

    pair = await auth_service.login(
        command=LoginCommand(login=login, password=SecretStr("pw")),
        client_metadata=_CLIENT_METADATA,
    )

    assert pair.access_token.get_secret_value()
    assert len(fake_refresh_token_repository.by_hash) == 1
    fake_auth_uow.commit_mock.assert_awaited_once()


@pytest.mark.parametrize("login", ["Neo", "neo", "NEO"])
async def test_login_with_username_returns_token_pair(
    auth_service: AuthService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
    login: str,
) -> None:
    """Вход по username (в любом регистре) тоже выдаёт пару токенов."""
    await fake_user_credentials_repository.insert_user_credentials(
        make_user_credentials(
            email="neo@example.com",
            username="Neo",
            password=make_password(fake_salted_hasher.hash("pw")),
        ),
    )

    pair = await auth_service.login(
        command=LoginCommand(login=login, password=SecretStr("pw")),
        client_metadata=_CLIENT_METADATA,
    )

    assert pair.access_token.get_secret_value()
    assert len(fake_refresh_token_repository.by_hash) == 1


async def test_login_unknown_login_raises_invalid_credentials(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
) -> None:
    """Несуществующий логин → ``InvalidCredentialsError`` без refresh и коммита; пароль всё равно хешируется."""
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(
            command=LoginCommand(login="ghost@example.com", password=SecretStr("pw")),
            client_metadata=_CLIENT_METADATA,
        )

    assert fake_refresh_token_repository.by_hash == {}
    fake_auth_uow.commit_mock.assert_not_awaited()
    assert fake_salted_hasher.hashed_secrets == ["pw"]


async def test_login_wrong_password_raises_invalid_credentials(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
) -> None:
    """Верный логин и неверный пароль → ``InvalidCredentialsError`` без refresh и коммита."""
    await fake_user_credentials_repository.insert_user_credentials(
        make_user_credentials(
            email="neo@example.com",
            username="neo",
            password=make_password(fake_salted_hasher.hash("correct")),
        ),
    )

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(
            command=LoginCommand(login="neo@example.com", password=SecretStr("wrong")),
            client_metadata=_CLIENT_METADATA,
        )

    assert fake_refresh_token_repository.by_hash == {}
    fake_auth_uow.commit_mock.assert_not_awaited()


# --- logout -----------------------------------------------------------------


async def test_logout_revokes_active_token(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """Известный активный секрет: токен отозван, коммит."""
    secret = "live-secret"
    refresh_token_entity = make_refresh_token(token_hash=token_issuer.hash_refresh_secret(secret), revoked_at=None)
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity)

    await auth_service.logout(secret)

    assert refresh_token_entity.is_revoked
    fake_auth_uow.commit_mock.assert_awaited_once()


async def test_logout_without_secret_does_nothing(auth_service: AuthService, fake_auth_uow: FakeAuthUnitOfWork) -> None:
    """Без cookie (``None``) ничего не происходит, коммита нет."""
    await auth_service.logout(None)

    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_logout_unknown_secret_does_nothing(auth_service: AuthService, fake_auth_uow: FakeAuthUnitOfWork) -> None:
    """Неизвестный секрет — ничего не происходит, коммита нет."""
    await auth_service.logout("unknown")

    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_logout_revoked_token_does_nothing(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """Уже отозванный токен: выход идемпотентен, повторного коммита нет."""
    secret = "revoked-secret"
    refresh_token_entity = make_refresh_token(
        token_hash=token_issuer.hash_refresh_secret(secret),
        revoked_at=dt.datetime.now(tz=dt.UTC),
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity)

    await auth_service.logout(secret)

    fake_auth_uow.commit_mock.assert_not_awaited()


# --- refresh ----------------------------------------------------------------


async def test_refresh_rotates_token_and_returns_new_pair(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
    deterministic_hasher: Sha256DeterministicHasher,
) -> None:
    """Валидный секрет: старый токен отозван, выпущен новый активный, коммит."""
    user_credentials_entity = make_user_credentials()
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    secret = "live-secret"
    old_token = make_refresh_token(
        user_id=user_credentials_entity.user_id,
        token_hash=token_issuer.hash_refresh_secret(secret),
        revoked_at=None,
    )
    await fake_refresh_token_repository.insert_refresh_token(old_token)

    pair = await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert old_token.is_revoked
    new_hash = deterministic_hasher.digest(pair.refresh_token.secret.get_secret_value())
    assert new_hash != old_token.token_hash
    assert new_hash in fake_refresh_token_repository.by_hash
    assert not fake_refresh_token_repository.by_hash[new_hash].is_revoked
    fake_auth_uow.commit_mock.assert_awaited_once()


async def test_refresh_unknown_secret_raises_invalid_refresh_token(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
) -> None:
    """Неизвестный секрет → ``InvalidRefreshTokenError``, без коммита."""
    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret="ghost", client_metadata=_CLIENT_METADATA)

    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_refresh_reuse_detection_revokes_all_active_and_raises(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """Уже отозванный секрет (повторное использование) → отозваны все активные токены, ``InvalidRefreshTokenError``."""
    user_id = uuid4()
    secret = "leaked-secret"
    reused = make_refresh_token(
        user_id=user_id,
        token_hash=token_issuer.hash_refresh_secret(secret),
        revoked_at=dt.datetime.now(tz=dt.UTC),
    )
    other_active = make_refresh_token(user_id=user_id, token_hash="other-active-hash", revoked_at=None)
    await fake_refresh_token_repository.insert_refresh_token(reused)
    await fake_refresh_token_repository.insert_refresh_token(other_active)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert other_active.is_revoked
    fake_auth_uow.commit_mock.assert_awaited_once()


async def test_refresh_expired_token_raises_without_side_effects(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """Истёкший, но не отозванный токен → ``InvalidRefreshTokenError`` без побочных эффектов."""
    secret = "expired-secret"
    refresh_token_entity = make_refresh_token(
        token_hash=token_issuer.hash_refresh_secret(secret),
        revoked_at=None,
        expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1),
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert not refresh_token_entity.is_revoked
    fake_auth_uow.commit_mock.assert_not_awaited()


async def test_refresh_missing_account_raises_invalid_refresh_token(
    auth_service: AuthService,
    fake_auth_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """Валидный токен, но учётной записи нет → ``InvalidRefreshTokenError``; старый токен не тронут, коммита нет."""
    secret = "orphan-secret"
    refresh_token_entity = make_refresh_token(
        token_hash=token_issuer.hash_refresh_secret(secret),
        revoked_at=None,
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert not refresh_token_entity.is_revoked
    fake_auth_uow.commit_mock.assert_not_awaited()
