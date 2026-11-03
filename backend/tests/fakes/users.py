"""
In-memory фейки домена users: репозиторий и UoW.

Реализуют порты из ``app.users.application.ports.*`` — тот же контракт, что и боевой
SQLAlchemy-репозиторий/UoW. ``ty`` сверяет обе реализации с портом, поэтому фейк не
может молча разойтись с реальной сигнатурой. Сторадж — ``dict`` по ``user_id``;
сущность кладётся по ссылке (моделирует identity map SA-сессии).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import UUID

from app.users.application.ports.unit_of_work import UserUnitOfWorkPort
from app.users.application.ports.user_repository import UserRepositoryPort
from app.users.domain.entities import UserEntity


class FakeUserRepository(UserRepositoryPort):
    """Фейк хранилища пользователей поверх ``dict`` по ``user_id``."""

    def __init__(self) -> None:
        self.by_user_id: dict[UUID, UserEntity] = {}

    async def insert_user(self, user_entity: UserEntity) -> None:
        self.by_user_id[user_entity.user_id] = user_entity

    async def find_user_by_id(self, user_id: UUID) -> UserEntity | None:
        return self.by_user_id.get(user_id)


class FakeUserUnitOfWork(UserUnitOfWorkPort):
    """
    In-memory UoW.

    Репозиторий передаётся снаружи (фикстура держит тот же инстанс, чтобы тест мог
    проверять его состояние), ``commit`` — ``AsyncMock`` (``commit_mock``) для проверки
    факта фиксации.
    """

    def __init__(self, *, user_repository: UserRepositoryPort) -> None:
        self.user_repository = user_repository
        self.commit_mock = AsyncMock()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        yield

    async def commit(self) -> None:
        await self.commit_mock()
