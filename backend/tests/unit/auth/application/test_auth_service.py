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
from app.shared.infra.crypto.sha256 import Sha256DeterministicHasher
from tests.builders import make_password, make_refresh_token, make_user_credentials
from tests.fakes import (
    FakeAuthUnitOfWork,
    FakeEmailVerificationService,
    FakeRefreshTokenRepository,
    FakeSaltedHasher,
    FakeUserCredentialsRepository,
    FakeUsersClient,
)

_CLIENT_METADATA = ClientMetadata(ip_address="1.2.3.4", user_agent="UA")


# --- register ---------------------------------------------------------------


async def test_register_persists_credentials_calls_users_and_requests_verification(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_users_client: FakeUsersClient,
    fake_email_verification_service: FakeEmailVerificationService,
    fake_salted_hasher: FakeSaltedHasher,
    deterministic_hasher: Sha256DeterministicHasher,
) -> None:
    """register: хеширует пароль, сохраняет creds, зовёт users-сервис, кладёт refresh, коммитит и просит верификацию."""
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
    assert stored.password.hash == fake_salted_hasher.hash(secret="pw")

    assert len(fake_users_client.created) == 1
    created = fake_users_client.created[0]
    assert created.user_id == stored.user_id
    assert created.display_name == "neo"
    assert created.marketing_emails_consent is True
    assert created.terms_accepted_at == stored.created_at

    stored_hash = deterministic_hasher.digest(secret=pair.refresh_token.secret.get_secret_value())
    assert stored_hash in fake_refresh_token_repository.by_hash

    fake_uow.commit_mock.assert_awaited_once()
    assert fake_email_verification_service.requested_user_ids == [stored.user_id]


@pytest.mark.parametrize("email", ["neo@example.com", "NEO@Example.com"])
async def test_register_raises_when_email_already_exists(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_users_client: FakeUsersClient,
    email: str,
) -> None:
    """register: занятый email (в любом регистре) → EmailAlreadyExistError, без новой записи, вызова users и коммита."""
    await fake_user_credentials_repository.insert_user_credentials(
        user_credentials_entity=make_user_credentials(email="neo@example.com", username="existing"),
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
    fake_uow.commit_mock.assert_not_awaited()


async def test_register_does_not_commit_when_users_creation_fails(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_users_client: FakeUsersClient,
    fake_email_verification_service: FakeEmailVerificationService,
) -> None:
    """register: сбой создания users-профиля → ошибка проброшена, без commit (полный rollback) и без верификации."""
    fake_users_client.error = RuntimeError("users service down")
    command = RegistrationCommand(
        username="neo",
        email="neo@example.com",
        password=SecretStr("pw"),
        marketing_emails_consent=True,
    )

    with pytest.raises(RuntimeError, match="users service down"):
        await auth_service.register(command=command, client_metadata=_CLIENT_METADATA)

    fake_uow.commit_mock.assert_not_awaited()
    assert fake_email_verification_service.requested_user_ids == []


@pytest.mark.parametrize("username", ["neo", "NeO"])
async def test_register_raises_when_username_already_taken(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    username: str,
) -> None:
    """register: свободный email, но занятый username (в любом регистре) → UsernameAlreadyExistError, без коммита."""
    await fake_user_credentials_repository.insert_user_credentials(
        user_credentials_entity=make_user_credentials(email="taken@example.com", username="neo"),
    )
    command = RegistrationCommand(
        username=username,
        email="new@example.com",
        password=SecretStr("pw"),
        marketing_emails_consent=False,
    )

    with pytest.raises(UsernameAlreadyExistError):
        await auth_service.register(command=command, client_metadata=_CLIENT_METADATA)

    fake_uow.commit_mock.assert_not_awaited()


# --- login ------------------------------------------------------------------


@pytest.mark.parametrize("login", ["neo@example.com", "NEO@Example.COM"])
async def test_login_with_email_returns_token_pair(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
    login: str,
) -> None:
    """login по email (в любом регистре) с верным паролем выдаёт пару токенов и сохраняет refresh."""
    await fake_user_credentials_repository.insert_user_credentials(
        user_credentials_entity=make_user_credentials(
            email="neo@example.com",
            username="neo",
            password=make_password(hash=fake_salted_hasher.hash(secret="pw")),
        ),
    )

    pair = await auth_service.login(
        command=LoginCommand(login=login, password=SecretStr("pw")),
        client_metadata=_CLIENT_METADATA,
    )

    assert pair.access_token.get_secret_value()
    assert len(fake_refresh_token_repository.by_hash) == 1
    fake_uow.commit_mock.assert_awaited_once()


@pytest.mark.parametrize("login", ["Neo", "neo", "NEO"])
async def test_login_with_username_returns_token_pair(
    auth_service: AuthService,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
    login: str,
) -> None:
    """login по username (в любом регистре), а не email, тоже работает."""
    await fake_user_credentials_repository.insert_user_credentials(
        user_credentials_entity=make_user_credentials(
            email="neo@example.com",
            username="Neo",
            password=make_password(hash=fake_salted_hasher.hash(secret="pw")),
        ),
    )

    pair = await auth_service.login(
        command=LoginCommand(login=login, password=SecretStr("pw")),
        client_metadata=_CLIENT_METADATA,
    )

    assert pair.access_token.get_secret_value()
    assert len(fake_refresh_token_repository.by_hash) == 1


async def test_login_raises_when_user_not_found(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
) -> None:
    """login: несуществующий логин → InvalidCredentialsError без refresh и коммита; пароль всё равно хешируется."""
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(
            command=LoginCommand(login="ghost@example.com", password=SecretStr("pw")),
            client_metadata=_CLIENT_METADATA,
        )

    assert fake_refresh_token_repository.by_hash == {}
    fake_uow.commit_mock.assert_not_awaited()
    assert fake_salted_hasher.hashed_secrets == ["pw"]


async def test_login_raises_when_password_wrong(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    fake_salted_hasher: FakeSaltedHasher,
) -> None:
    """login: верный логин, неверный пароль → InvalidCredentialsError, без refresh и коммита."""
    await fake_user_credentials_repository.insert_user_credentials(
        user_credentials_entity=make_user_credentials(
            email="neo@example.com",
            username="neo",
            password=make_password(hash=fake_salted_hasher.hash(secret="correct")),
        ),
    )

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(
            command=LoginCommand(login="neo@example.com", password=SecretStr("wrong")),
            client_metadata=_CLIENT_METADATA,
        )

    assert fake_refresh_token_repository.by_hash == {}
    fake_uow.commit_mock.assert_not_awaited()


# --- logout -----------------------------------------------------------------


async def test_logout_revokes_active_token(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """logout: известный активный секрет отзывает токен и коммитит."""
    secret = "live-secret"
    refresh_token_entity = make_refresh_token(
        token_hash=token_issuer.hash_refresh_secret(refresh_secret=secret), revoked_at=None
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity=refresh_token_entity)

    await auth_service.logout(refresh_secret=secret)

    assert refresh_token_entity.is_revoked
    fake_uow.commit_mock.assert_awaited_once()


async def test_logout_noop_when_secret_is_none(auth_service: AuthService, fake_uow: FakeAuthUnitOfWork) -> None:
    """logout без cookie (None) — молча ничего не делает, без коммита."""
    await auth_service.logout(refresh_secret=None)

    fake_uow.commit_mock.assert_not_awaited()


async def test_logout_noop_when_token_unknown(auth_service: AuthService, fake_uow: FakeAuthUnitOfWork) -> None:
    """logout с неизвестным секретом — молча ничего не делает, без коммита."""
    await auth_service.logout(refresh_secret="unknown")

    fake_uow.commit_mock.assert_not_awaited()


async def test_logout_noop_when_token_already_revoked(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """logout по уже отозванному токену идемпотентен — без повторного коммита."""
    secret = "revoked-secret"
    refresh_token_entity = make_refresh_token(
        token_hash=token_issuer.hash_refresh_secret(refresh_secret=secret),
        revoked_at=dt.datetime.now(tz=dt.UTC),
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity=refresh_token_entity)

    await auth_service.logout(refresh_secret=secret)

    fake_uow.commit_mock.assert_not_awaited()


# --- refresh ----------------------------------------------------------------


async def test_refresh_rotates_token_and_returns_new_pair(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
    deterministic_hasher: Sha256DeterministicHasher,
) -> None:
    """refresh валидным секретом: старый токен revoked, выпущен новый активный, коммит."""
    user_credentials_entity = make_user_credentials()
    await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity=user_credentials_entity)
    secret = "live-secret"
    old_token = make_refresh_token(
        user_id=user_credentials_entity.user_id,
        token_hash=token_issuer.hash_refresh_secret(refresh_secret=secret),
        revoked_at=None,
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity=old_token)

    pair = await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert old_token.is_revoked
    new_hash = deterministic_hasher.digest(secret=pair.refresh_token.secret.get_secret_value())
    assert new_hash != old_token.token_hash
    assert new_hash in fake_refresh_token_repository.by_hash
    assert not fake_refresh_token_repository.by_hash[new_hash].is_revoked
    fake_uow.commit_mock.assert_awaited_once()


async def test_refresh_raises_when_secret_unknown(auth_service: AuthService, fake_uow: FakeAuthUnitOfWork) -> None:
    """refresh неизвестным секретом → InvalidRefreshTokenError, без коммита."""
    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret="ghost", client_metadata=_CLIENT_METADATA)

    fake_uow.commit_mock.assert_not_awaited()


async def test_refresh_reuse_detection_revokes_all_active_and_raises(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """refresh уже отозванным секретом (reuse) → отзыв всех активных токенов пользователя + 401."""
    user_id = uuid4()
    secret = "leaked-secret"
    reused = make_refresh_token(
        user_id=user_id,
        token_hash=token_issuer.hash_refresh_secret(refresh_secret=secret),
        revoked_at=dt.datetime.now(tz=dt.UTC),
    )
    other_active = make_refresh_token(user_id=user_id, token_hash="other-active-hash", revoked_at=None)
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity=reused)
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity=other_active)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert other_active.is_revoked
    fake_uow.commit_mock.assert_awaited_once()


async def test_refresh_raises_when_token_expired_without_side_effects(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """refresh истёкшим (но не отозванным) токеном → 401 без побочных эффектов."""
    secret = "expired-secret"
    refresh_token_entity = make_refresh_token(
        token_hash=token_issuer.hash_refresh_secret(refresh_secret=secret),
        revoked_at=None,
        expires_at=dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1),
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity=refresh_token_entity)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert not refresh_token_entity.is_revoked
    fake_uow.commit_mock.assert_not_awaited()


async def test_refresh_raises_when_credentials_missing(
    auth_service: AuthService,
    fake_uow: FakeAuthUnitOfWork,
    fake_refresh_token_repository: FakeRefreshTokenRepository,
    token_issuer: TokenIssuer,
) -> None:
    """refresh валидным токеном, но аккаунт удалён → 401, старый токен не тронут, без коммита."""
    secret = "orphan-secret"
    refresh_token_entity = make_refresh_token(
        token_hash=token_issuer.hash_refresh_secret(refresh_secret=secret),
        revoked_at=None,
    )
    await fake_refresh_token_repository.insert_refresh_token(refresh_token_entity=refresh_token_entity)

    with pytest.raises(InvalidRefreshTokenError):
        await auth_service.refresh(refresh_secret=secret, client_metadata=_CLIENT_METADATA)

    assert not refresh_token_entity.is_revoked
    fake_uow.commit_mock.assert_not_awaited()
