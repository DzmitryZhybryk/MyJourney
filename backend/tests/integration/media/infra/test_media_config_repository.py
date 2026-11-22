"""
Интеграционные тесты версий конфига media против реального Postgres: JSONB-снапшот туда и обратно,
последняя версия по номеру, повтор номера как конфликт, seed поверх уже записанного конфига и seed поверх
строки, которую код уже не читает.
"""

import json
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.media.application.schemas.commands import SeedMediaConfigCommand
from app.media.application.services.media_config import MediaConfigService
from app.media.infra.repositories import MediaConfigRepository
from app.media.infra.uow import MediaUnitOfWork
from app.shared.versioned_config import ConfigVersionConflictError
from tests.builders import make_media_config_snapshot

ADMIN_ID = UUID("00000000-0000-0000-0000-0000000000ad")


async def test_find_latest_media_config_empty_table_returns_none(db_session: AsyncSession) -> None:
    """Пустая таблица — конфиг ещё не записан."""
    assert await MediaConfigRepository(db_session).find_latest_media_config() is None


async def test_find_latest_media_config_returns_highest_version_with_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Последняя версия — с наибольшим номером; снапшот читается из JSONB той же моделью."""
    edited = make_media_config_snapshot(avatar_max_size_bytes=1_000)
    async with session_factory() as session:
        repository = MediaConfigRepository(session)
        await repository.insert_media_config(version=1, snapshot=make_media_config_snapshot(), created_by=None)
        await repository.insert_media_config(version=2, snapshot=edited, created_by=ADMIN_ID)
        await session.commit()

    async with session_factory() as reader:
        latest = await MediaConfigRepository(reader).find_latest_media_config()

    assert latest is not None
    assert (latest.version, latest.snapshot, latest.created_by) == (2, edited, ADMIN_ID)
    assert latest.created_at.tzinfo is not None


async def test_insert_media_config_existing_version_raises_conflict(db_session: AsyncSession) -> None:
    """Повтор номера версии — нарушение первичного ключа, переведённое в конфликт конфига."""
    repository = MediaConfigRepository(db_session)
    await repository.insert_media_config(version=1, snapshot=make_media_config_snapshot(), created_by=None)

    with pytest.raises(ConfigVersionConflictError):
        await repository.insert_media_config(version=1, snapshot=make_media_config_snapshot(), created_by=ADMIN_ID)


async def test_seed_media_config_second_run_keeps_edited_config(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Повторный деплой не перезаписывает конфиг: в таблице остаётся одна версия от первого seed."""
    for avatar_max_size_bytes in (1_000, 2_000):
        async with session_factory() as session:
            await MediaConfigService(MediaUnitOfWork(session)).seed_media_config(
                SeedMediaConfigCommand(make_media_config_snapshot(avatar_max_size_bytes=avatar_max_size_bytes))
            )

    async with session_factory() as reader:
        latest = await MediaConfigRepository(reader).find_latest_media_config()

    assert latest is not None
    assert (latest.version, latest.snapshot.avatar.max_size_bytes) == (1, 1_000)


async def test_seed_media_config_latest_row_of_old_shape_fails_and_writes_nothing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Строка формы, которую код уже не читает, останавливает seed, а не затирается начальными значениями."""
    old_shape_snapshot = make_media_config_snapshot().model_dump(mode="json")
    del old_shape_snapshot["avatar"]["min_side"]
    async with session_factory() as session:
        await session.execute(
            text("INSERT INTO media_config (version, created_at, config) VALUES (1, now(), CAST(:config AS jsonb))"),
            {"config": json.dumps(old_shape_snapshot)},
        )
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(ValidationError):
            await MediaConfigService(MediaUnitOfWork(session)).seed_media_config(
                SeedMediaConfigCommand(make_media_config_snapshot())
            )

    async with session_factory() as reader:
        versions = (await reader.scalars(text("SELECT version FROM media_config"))).all()

    assert versions == [1]
