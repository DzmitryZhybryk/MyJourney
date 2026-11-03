"""
In-memory фейки auth: репозитории, UoW, клиент к users и сервис подтверждения email.

Каждый фейк реализует соответствующий порт из ``app.auth.application.ports.*`` —
тот же контракт, что и реальный SQLAlchemy-репозиторий. ``ty`` сверяет обе
реализации с портом, поэтому фейк не может молча разойтись с боевой сигнатурой.

Сторадж — обычные ``dict``/``list``; сущности кладутся и достаются по ссылке,
поэтому доменные мутации (``revoke()``, ``mark_used()``) видны без отдельного
``update``-вызова (моделирует identity map SQLAlchemy-сессии).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports.challenge_repository import ChallengeRepositoryPort
from app.auth.application.ports.refresh_token_repository import RefreshTokenRepositoryPort
from app.auth.application.ports.unit_of_work import AuthUnitOfWorkPort
from app.auth.application.ports.user_credentials_repository import UserCredentialsRepositoryPort
from app.auth.application.ports.users_client import CreateUserRequest, UsersClientPort
from app.auth.application.services.email_verification import EmailVerificationService
from app.auth.domain.entities import ChallengeEntity, RefreshTokenEntity, UserCredentialsEntity
from app.auth.domain.enums import ChallengeTypeEnum


class FakeUserCredentialsRepository(UserCredentialsRepositoryPort):
    """Фейк хранилища учётных данных поверх ``dict`` по ``user_id``."""

    def __init__(self) -> None:
        self.by_user_id: dict[UUID, UserCredentialsEntity] = {}

    async def insert_user_credentials(self, user_credentials_entity: UserCredentialsEntity) -> None:
        self.by_user_id[user_credentials_entity.user_id] = user_credentials_entity

    async def update_user_credentials_by_user_id(self, user_credentials_entity: UserCredentialsEntity) -> None:
        self.by_user_id[user_credentials_entity.user_id] = user_credentials_entity

    async def find_user_credentials_by_user_id(self, user_id: UUID) -> UserCredentialsEntity | None:
        return self.by_user_id.get(user_id)

    async def find_user_credentials_by_email(self, email: str) -> UserCredentialsEntity | None:
        return next((c for c in self.by_user_id.values() if c.email.lower() == email.lower()), None)

    async def find_user_credentials_by_username(self, username: str) -> UserCredentialsEntity | None:
        return next((c for c in self.by_user_id.values() if c.username.lower() == username.lower()), None)

    async def find_user_credentials_by_login(self, login: str) -> UserCredentialsEntity | None:
        return await self.find_user_credentials_by_email(email=login) or await self.find_user_credentials_by_username(
            username=login
        )


class FakeRefreshTokenRepository(RefreshTokenRepositoryPort):
    """Фейк хранилища refresh-токенов поверх ``dict`` по ``token_hash``."""

    def __init__(self) -> None:
        self.by_hash: dict[str, RefreshTokenEntity] = {}

    async def insert_refresh_token(self, refresh_token_entity: RefreshTokenEntity) -> None:
        self.by_hash[refresh_token_entity.token_hash] = refresh_token_entity

    async def find_refresh_token_by_hash_for_update(self, token_hash: str) -> RefreshTokenEntity | None:
        return self.by_hash.get(token_hash)

    async def update_refresh_token_by_id(self, refresh_token_entity: RefreshTokenEntity) -> None:
        # Сущность мутируется на месте; стор держит ту же ссылку — переписываем для явности.
        self.by_hash[refresh_token_entity.token_hash] = refresh_token_entity

    async def revoke_all_active_refresh_tokens_by_user_id(self, user_id: UUID) -> None:
        for refresh_token_entity in self.by_hash.values():
            if refresh_token_entity.user_id == user_id and not refresh_token_entity.is_revoked:
                refresh_token_entity.revoke()


class FakeChallengeRepository(ChallengeRepositoryPort):
    """Фейк хранилища challenge'ей поверх ``list`` (хранит и активные, и использованные)."""

    def __init__(self) -> None:
        self.challenges: list[ChallengeEntity] = []

    async def insert_challenge(self, challenge_entity: ChallengeEntity) -> None:
        self.challenges.append(challenge_entity)

    async def find_active_challenge_for_update(
        self,
        *,
        user_id: UUID,
        challenge_type: ChallengeTypeEnum,
    ) -> ChallengeEntity | None:
        return next(
            (
                c
                for c in self.challenges
                if c.user_id == user_id and c.challenge_type == challenge_type and c.used_at is None
            ),
            None,
        )

    async def update_challenge_by_id(self, challenge_entity: ChallengeEntity) -> None:
        """No-op: сущность мутируется на месте, список держит ту же ссылку."""


class FakeAuthUnitOfWork(AuthUnitOfWorkPort):
    """
    In-memory UoW.

    Репозитории передаются снаружи (фикстуры держат те же инстансы, чтобы тест
    мог проверять их состояние), ``commit``/``flush`` — ``AsyncMock``
    (``commit_mock``/``flush_mock``) для проверки факта фиксации/сброса,
    ``transaction`` — no-op область (rollback реальной сессии проверяется в
    integration), ``session`` — sentinel: фейк-bus её не использует, но тест
    сверяет, что atomic-defer сделан именно в этой сессии. Порядок INSERT'ов на
    ``flush`` (FK-зависимости) проверяется только на реальном Postgres в integration.
    """

    def __init__(
        self,
        *,
        user_credentials_repository: UserCredentialsRepositoryPort,
        refresh_token_repository: RefreshTokenRepositoryPort,
        challenge_repository: ChallengeRepositoryPort,
    ) -> None:
        self.user_credentials_repository = user_credentials_repository
        self.refresh_token_repository = refresh_token_repository
        self.challenge_repository = challenge_repository
        self.commit_mock = AsyncMock()
        self.flush_mock = AsyncMock()
        self._session = cast(AsyncSession, object())

    @property
    def session(self) -> AsyncSession:
        return self._session

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        yield

    async def flush(self) -> None:
        await self.flush_mock()

    async def commit(self) -> None:
        await self.commit_mock()


class FakeUsersClient(UsersClientPort):
    """
    Записывает каждый ``create_user`` в ``created`` вместо реального вызова users-сервиса.

    Тест может выставить ``error`` — тогда ``create_user`` поднимает его вместо записи,
    моделируя сбой создания users-профиля (например, для проверки атомарного rollback'а register).
    """

    def __init__(self) -> None:
        self.created: list[CreateUserRequest] = []
        self.error: Exception | None = None

    async def create_user(self, request: CreateUserRequest) -> None:
        if self.error is not None:
            raise self.error

        self.created.append(request)


class FakeEmailVerificationService(EmailVerificationService):
    """
    Подменяет реальный ``EmailVerificationService`` в тестах ``AuthService``.

    ``__init__`` без зависимостей; ``request_email_verification`` лишь записывает
    ``user_id`` в ``requested_user_ids`` — register-флоу проверяет, что верификация
    была запрошена, не дёргая настоящий сервис.
    """

    def __init__(self) -> None:
        self.requested_user_ids: list[UUID] = []

    async def request_email_verification(self, user_id: UUID) -> None:
        self.requested_user_ids.append(user_id)
