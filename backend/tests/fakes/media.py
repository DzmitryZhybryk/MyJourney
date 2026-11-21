"""
Фейки media: репозиторий версий конфига и UoW вокруг него; сырой поток ответа S3 — тело ``GetObject``
для ``StreamingBody`` aiobotocore без сети.
"""

import datetime as dt
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import UUID

from app.media.application.ports.media_config_repository import (
    MediaConfigRepositoryPort,
    MediaConfigSnapshot,
    StoredMediaConfig,
)
from app.media.application.ports.unit_of_work import MediaUnitOfWorkPort
from app.shared.versioned_config import ConfigVersionConflictError


class FakeMediaConfigRepository(MediaConfigRepositoryPort):
    """
    Версии конфига поверх ``dict`` номер → версия: последняя — с наибольшим номером, повтор номера —
    ``ConfigVersionConflictError``, как нарушение первичного ключа в боевой таблице.
    """

    def __init__(self) -> None:
        self.versions: dict[int, StoredMediaConfig] = {}

    async def find_latest_media_config(self) -> StoredMediaConfig | None:
        return self.versions[max(self.versions)] if self.versions else None

    async def insert_media_config(
        self, *, version: int, snapshot: MediaConfigSnapshot, created_by: UUID | None
    ) -> None:
        if version in self.versions:
            raise ConfigVersionConflictError()

        self.versions[version] = StoredMediaConfig(
            version=version,
            snapshot=snapshot,
            created_at=dt.datetime.now(tz=dt.UTC),
            created_by=created_by,
        )


class FakeMediaUnitOfWork(MediaUnitOfWorkPort):
    """In-memory UoW media: фейк-репозиторий конфига + мокнутый ``commit`` и no-op ``transaction``."""

    def __init__(self, *, media_config_repository: MediaConfigRepositoryPort) -> None:
        self.media_config_repository = media_config_repository
        self.commit_mock = AsyncMock()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        yield

    async def commit(self) -> None:
        await self.commit_mock()


class FakeS3ResponseContent:
    """
    Поток содержимого ответа: отдаёт заданные байты или падает заданной ошибкой.

    ``error`` моделирует обрыв соединения посреди тела.
    """

    def __init__(self, *, body: bytes, error: Exception | None) -> None:
        self._body = body
        self._error = error

    async def read(self, amount: int = -1) -> bytes:
        if self._error is not None:
            raise self._error

        if amount < 0:
            chunk, self._body = self._body, b""
        else:
            chunk, self._body = self._body[:amount], self._body[amount:]

        return chunk


class FakeS3ResponseStream:
    """
    Сырой ответ, который ``StreamingBody`` читает через ``content`` и закрывает через ``close``.

    ``is_closed`` показывает, закрыл ли читатель поток.
    """

    def __init__(self, *, body: bytes, error: Exception | None = None) -> None:
        self.content = FakeS3ResponseContent(body=body, error=error)
        self.url = "http://s3.localhost:9050"
        self.is_closed = False

    def close(self) -> None:
        self.is_closed = True
