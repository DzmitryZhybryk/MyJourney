from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol

from app.users.application.ports.user_repository import UserRepositoryPort

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["UserUnitOfWorkPort"]


class UserUnitOfWorkPort(Protocol):
    """
    Контракт транзакционной границы users, на который опирается ``UserService``.

    Объединяет доступ к репозиторию (через его порт), транзакционную область
    ``transaction()`` + явный ``commit`` и «сырую» сессию, в транзакции которой
    публикуется событие о профиле (``event_publisher.bind_to(uow.session)``).
    """

    user_repository: UserRepositoryPort

    @property
    def session(self) -> AsyncSession: ...

    def transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def commit(self) -> None: ...
