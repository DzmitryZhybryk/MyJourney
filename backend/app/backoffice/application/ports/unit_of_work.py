from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.backoffice.application.ports.account_repository import AccountRepositoryPort

__all__ = ["BackofficeUnitOfWorkPort"]


class BackofficeUnitOfWorkPort(Protocol):
    """Контракт транзакционной границы backoffice: репозиторий, транзакционная область и явный ``commit``."""

    account_repository: AccountRepositoryPort

    def transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def commit(self) -> None: ...
