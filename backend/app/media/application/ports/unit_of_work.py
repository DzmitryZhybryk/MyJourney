from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.media.application.ports.media_config_repository import MediaConfigRepositoryPort

__all__ = ["MediaUnitOfWorkPort"]


class MediaUnitOfWorkPort(Protocol):
    """Транзакционная граница media: репозиторий конфига, область ``transaction()`` и явный ``commit``."""

    media_config_repository: MediaConfigRepositoryPort

    def transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def commit(self) -> None: ...
