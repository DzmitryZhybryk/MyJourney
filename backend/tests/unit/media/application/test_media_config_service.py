from uuid import UUID

import pytest

from app.media.application.ports.media_config_repository import MediaConfigSnapshot, StoredMediaConfig
from app.media.application.schemas.commands import SeedMediaConfigCommand, UpdateMediaConfigCommand
from app.media.application.services.media_config import MediaConfigService
from app.media.domain.enums import SideAxisEnum
from app.shared.versioned_config import ConfigMissingError, ConfigVersionConflictError
from tests.builders import make_media_config_snapshot
from tests.fakes import FakeMediaConfigRepository, FakeMediaUnitOfWork

ADMIN_ID = UUID("00000000-0000-0000-0000-0000000000ad")


async def test_get_upload_rules_latest_version_joins_rules_with_side_axis(
    media_config_service: MediaConfigService,
    fake_media_config_repository: FakeMediaConfigRepository,
) -> None:
    """Правила берутся из последней версии, ось минимальной стороны — из кода для каждого вида-картинки."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=None
    )
    await fake_media_config_repository.insert_media_config(
        version=2, snapshot=make_media_config_snapshot(avatar_max_size_bytes=1_000), created_by=ADMIN_ID
    )

    result = await media_config_service.get_upload_rules()

    assert result.avatar.max_size_bytes == 1_000
    assert result.avatar.min_side_axis is SideAxisEnum.SHORT
    assert result.journey_photo.min_side_axis is SideAxisEnum.LONG
    assert result.journey_video.max_size_bytes == 209_715_200


async def test_get_upload_rules_no_config_raises_config_missing(media_config_service: MediaConfigService) -> None:
    """Без единой версии конфига правил нет — это сбой развёртывания, а не пустой ответ."""
    with pytest.raises(ConfigMissingError):
        await media_config_service.get_upload_rules()


async def test_get_media_config_returns_latest_version_with_author(
    media_config_service: MediaConfigService,
    fake_media_config_repository: FakeMediaConfigRepository,
) -> None:
    """Админ видит последнюю версию: номер, снапшот и кто её записал."""
    snapshot = make_media_config_snapshot(avatar_min_side=640)
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=None
    )
    await fake_media_config_repository.insert_media_config(version=2, snapshot=snapshot, created_by=ADMIN_ID)

    result = await media_config_service.get_media_config()

    assert (result.version, result.snapshot, result.created_by) == (2, snapshot, ADMIN_ID)


async def test_get_media_config_no_config_raises_config_missing(media_config_service: MediaConfigService) -> None:
    """Админский экран без записанного конфига — тот же сбой развёртывания."""
    with pytest.raises(ConfigMissingError):
        await media_config_service.get_media_config()


async def test_seed_media_config_empty_store_writes_version_one_by_deploy(
    media_config_service: MediaConfigService,
    fake_media_config_repository: FakeMediaConfigRepository,
    fake_media_uow: FakeMediaUnitOfWork,
) -> None:
    """Пустая таблица получает версию 1 без автора, и запись фиксируется."""
    snapshot = make_media_config_snapshot()

    await media_config_service.seed_media_config(SeedMediaConfigCommand(snapshot))

    stored = fake_media_config_repository.versions[1]
    assert (stored.snapshot, stored.created_by) == (snapshot, None)
    fake_media_uow.commit_mock.assert_awaited_once()


async def test_seed_media_config_existing_config_left_untouched(
    media_config_service: MediaConfigService,
    fake_media_config_repository: FakeMediaConfigRepository,
    fake_media_uow: FakeMediaUnitOfWork,
) -> None:
    """Повторный деплой не трогает конфиг, который админ уже правил."""
    edited = make_media_config_snapshot(avatar_max_size_bytes=1_000)
    await fake_media_config_repository.insert_media_config(version=1, snapshot=edited, created_by=ADMIN_ID)

    await media_config_service.seed_media_config(SeedMediaConfigCommand(make_media_config_snapshot()))

    assert list(fake_media_config_repository.versions) == [1]
    assert fake_media_config_repository.versions[1].snapshot == edited
    fake_media_uow.commit_mock.assert_not_awaited()


async def test_seed_media_config_concurrent_seed_conflict_is_not_an_error() -> None:
    """Параллельный запуск успел записать версию 1 между чтением и вставкой — seed тихо уступает."""

    class RacingMediaConfigRepository(FakeMediaConfigRepository):
        async def find_latest_media_config(self) -> StoredMediaConfig | None:
            return None

        async def insert_media_config(
            self, *, version: int, snapshot: MediaConfigSnapshot, created_by: UUID | None
        ) -> None:
            raise ConfigVersionConflictError()

    uow = FakeMediaUnitOfWork(RacingMediaConfigRepository())

    await MediaConfigService(uow).seed_media_config(SeedMediaConfigCommand(make_media_config_snapshot()))

    uow.commit_mock.assert_not_awaited()


async def test_update_media_config_latest_version_writes_next_version_by_admin(
    media_config_service: MediaConfigService,
    fake_media_config_repository: FakeMediaConfigRepository,
    fake_media_uow: FakeMediaUnitOfWork,
) -> None:
    """Правка последней версии записывается следующим номером с автором из токена."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=None
    )
    edited = make_media_config_snapshot(avatar_max_size_bytes=1_000)

    await media_config_service.update_media_config(
        user_id=ADMIN_ID, command=UpdateMediaConfigCommand(edited_version=1, snapshot=edited)
    )

    stored = fake_media_config_repository.versions[2]
    assert (stored.snapshot, stored.created_by) == (edited, ADMIN_ID)
    fake_media_uow.commit_mock.assert_awaited_once()


async def test_update_media_config_unchanged_snapshot_writes_no_version(
    media_config_service: MediaConfigService,
    fake_media_config_repository: FakeMediaConfigRepository,
    fake_media_uow: FakeMediaUnitOfWork,
) -> None:
    """Сохранение без изменений не плодит версию и не переписывает автора последней правки."""
    await fake_media_config_repository.insert_media_config(
        version=1, snapshot=make_media_config_snapshot(), created_by=None
    )

    await media_config_service.update_media_config(
        user_id=ADMIN_ID,
        command=UpdateMediaConfigCommand(edited_version=1, snapshot=make_media_config_snapshot()),
    )

    assert list(fake_media_config_repository.versions) == [1]
    fake_media_uow.commit_mock.assert_not_awaited()


@pytest.mark.parametrize("edited_version", [1, 3], ids=["stale", "future"])
async def test_update_media_config_not_latest_version_raises_conflict(
    media_config_service: MediaConfigService,
    fake_media_config_repository: FakeMediaConfigRepository,
    fake_media_uow: FakeMediaUnitOfWork,
    edited_version: int,
) -> None:
    """Правка устаревшей или несуществующей версии не затирает текущую."""
    for version in (1, 2):
        await fake_media_config_repository.insert_media_config(
            version=version, snapshot=make_media_config_snapshot(), created_by=None
        )

    with pytest.raises(ConfigVersionConflictError):
        await media_config_service.update_media_config(
            user_id=ADMIN_ID,
            command=UpdateMediaConfigCommand(edited_version=edited_version, snapshot=make_media_config_snapshot()),
        )

    assert list(fake_media_config_repository.versions) == [1, 2]
    fake_media_uow.commit_mock.assert_not_awaited()


async def test_update_media_config_no_config_raises_config_missing(media_config_service: MediaConfigService) -> None:
    """Править нечего, пока конфиг не записан развёртыванием."""
    with pytest.raises(ConfigMissingError):
        await media_config_service.update_media_config(
            user_id=ADMIN_ID, command=UpdateMediaConfigCommand(edited_version=1, snapshot=make_media_config_snapshot())
        )
