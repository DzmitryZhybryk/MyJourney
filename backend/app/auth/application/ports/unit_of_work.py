from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol

from app.auth.application.ports.challenge_repository import ChallengeRepositoryPort
from app.auth.application.ports.refresh_token_repository import RefreshTokenRepositoryPort
from app.auth.application.ports.user_credentials_repository import UserCredentialsRepositoryPort

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["AuthUnitOfWorkPort"]


class AuthUnitOfWorkPort(Protocol):
    """
    Контракт транзакционной границы auth, на который опираются сервисы.

    Объединяет доступ к репозиториям (через их порты), транзакционную область
    ``transaction()`` + явный ``commit`` и «сырую» сессию для atomic-defer'а
    procrastinate-таски в текущей транзакции (``task_bus.bind_to(uow.session)``).
    ``session`` типизирована ``AsyncSession`` осознанно: этот шов уже заложен в
    ``BaseUnitOfWork`` ради atomic defer и инкапсулировать его глубже без
    передизайна механизма нельзя.
    """

    user_credentials_repository: UserCredentialsRepositoryPort
    refresh_token_repository: RefreshTokenRepositoryPort
    challenge_repository: ChallengeRepositoryPort

    @property
    def session(self) -> AsyncSession: ...

    def transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...
