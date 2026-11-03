from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports.challenge_repository import ChallengeRepositoryPort
from app.auth.application.ports.refresh_token_repository import RefreshTokenRepositoryPort
from app.auth.application.ports.unit_of_work import AuthUnitOfWorkPort
from app.auth.application.ports.user_credentials_repository import UserCredentialsRepositoryPort
from app.auth.infra.repositories import (
    ChallengeRepository,
    RefreshTokenRepository,
    UserCredentialsRepository,
)
from app.shared.infra.postgres.uow import BaseUnitOfWork


class AuthUnitOfWork(BaseUnitOfWork, AuthUnitOfWorkPort):
    # Атрибуты типизированы портами (а не конкретными репозиториями): сервисы
    # зависят от контракта, а тестовый UoW подставляет in-memory фейки тех же портов.
    user_credentials_repository: UserCredentialsRepositoryPort
    refresh_token_repository: RefreshTokenRepositoryPort
    challenge_repository: ChallengeRepositoryPort

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.user_credentials_repository = UserCredentialsRepository(session=session)
        self.refresh_token_repository = RefreshTokenRepository(session=session)
        self.challenge_repository = ChallengeRepository(session=session)
