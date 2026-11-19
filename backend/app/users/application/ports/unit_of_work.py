from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.users.application.ports.user_repository import UserRepositoryPort

__all__ = ["UserUnitOfWorkPort"]


class UserUnitOfWorkPort(Protocol):
    """
    Контракт транзакционной границы users, на который опирается ``UserService``.

    Объединяет доступ к репозиторию (через его порт), транзакционную область
    ``transaction()`` и явный ``commit``. В отличие от ``AuthUnitOfWorkPort`` здесь
    нет ``session``-шва: users-флоу не делает atomic-defer procrastinate-таски,
    поэтому raw-сессия в контракте не нужна (YAGNI).
    """

    user_repository: UserRepositoryPort

    def transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def commit(self) -> None: ...
