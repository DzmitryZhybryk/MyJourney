from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.journeys.application.ports.journey_repository import JourneyRepositoryPort

__all__ = ["JourneyUnitOfWorkPort"]


class JourneyUnitOfWorkPort(Protocol):
    """
    Контракт транзакционной границы journeys, на который опирается ``JourneyService``.

    Объединяет доступ к репозиторию (через его порт), транзакционную область
    ``transaction()`` и явный ``commit``. Как и ``UserUnitOfWorkPort``, без
    ``session``-шва: создание поездки не делает atomic-defer procrastinate-таски,
    поэтому raw-сессия в контракте не нужна (YAGNI).
    """

    journey_repository: JourneyRepositoryPort

    def transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def commit(self) -> None: ...
