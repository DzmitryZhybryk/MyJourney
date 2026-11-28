from uuid import UUID

from app.media.application.ports.media_config_repository import ImageKindRules, VideoKindRules
from app.media.application.ports.unit_of_work import MediaUnitOfWorkPort
from app.media.application.schemas.commands import SeedMediaConfigCommand, UpdateMediaConfigCommand
from app.media.application.schemas.results import (
    ImageUploadRules,
    MediaConfigResult,
    UploadRulesResult,
    VideoUploadRules,
)
from app.media.domain.kind_specs import AVATAR_SPEC, JOURNEY_PHOTO_SPEC, ImageKindSpec
from app.shared.logging import get_logger
from app.shared.versioned_config import ConfigMissingError, ConfigVersionConflictError, next_config_version

logger = get_logger(__name__)


class MediaConfigService:
    """Правила загрузки видов файлов: что можно загрузить и какого размера."""

    def __init__(self, uow: MediaUnitOfWorkPort) -> None:
        """
        Args:
            uow: Транзакция и репозиторий конфига
        """
        self._uow = uow

    async def get_upload_rules(self) -> UploadRulesResult:
        """
        Отдаёт правила загрузки каждого вида файла по последней версии конфига.

        Scenarios:
            - показ правил загрузки клиенту до выбора файла

        Returns:
            Правила каждого вида файла

        Raises:
            ConfigMissingError: Конфиг ещё не записан
        """
        async with self._uow.transaction():
            stored_media_config = await self._uow.media_config_repository.find_latest_media_config()

        if stored_media_config is None:
            raise ConfigMissingError(domain="media")

        snapshot = stored_media_config.snapshot
        return UploadRulesResult(
            avatar=_image_upload_rules(kind_rules=snapshot.avatar, kind_spec=AVATAR_SPEC),
            journey_photo=_image_upload_rules(kind_rules=snapshot.journey_photo, kind_spec=JOURNEY_PHOTO_SPEC),
            journey_video=_video_upload_rules(snapshot.journey_video),
        )

    async def seed_media_config(self, command: SeedMediaConfigCommand) -> None:
        """
        Записывает начальный конфиг версией 1, если конфига ещё нет; существующий не трогает.

        Наличие проверяется чтением, а не попыткой вставки: конфликт ключа Postgres пишет в свой лог как
        ERROR, и обычный деплой выглядел бы сбоем. Конфликт всё же возможен, если параллельный запуск
        успел раньше, — это не ошибка.

        Scenarios:
            - начальное значение конфига при развёртывании, до старта приложения

        Args:
            command: Начальный конфиг
        """
        async with self._uow.transaction():
            if await self._uow.media_config_repository.find_latest_media_config() is not None:
                logger.info("media.config_seed_skipped", reason="config_exists")
                return

            try:
                await self._uow.media_config_repository.insert_media_config(
                    version=1,
                    snapshot=command.snapshot,
                    created_by=None,
                )
            except ConfigVersionConflictError:
                logger.info("media.config_seed_skipped", reason="concurrent_seed")
                return

            await self._uow.commit()

        logger.info("media.config_seeded", version=1)

    async def get_media_config(self) -> MediaConfigResult:
        """
        Отдаёт последнюю версию конфига целиком: значения, номер версии, когда и кем записана.

        Scenarios:
            - экран правки конфига media у администратора

        Returns:
            Последняя версия конфига

        Raises:
            ConfigMissingError: Конфиг ещё не записан
        """
        async with self._uow.transaction():
            stored_media_config = await self._uow.media_config_repository.find_latest_media_config()

        if stored_media_config is None:
            raise ConfigMissingError(domain="media")

        return MediaConfigResult(
            version=stored_media_config.version,
            snapshot=stored_media_config.snapshot,
            created_at=stored_media_config.created_at,
            created_by=stored_media_config.created_by,
        )

    async def update_media_config(self, *, user_id: UUID, command: UpdateMediaConfigCommand) -> None:
        """
        Записывает новый конфиг следующей версией, если правили последнюю; конфиг без изменений не пишется.

        Scenarios:
            - администратор сохраняет конфиг media

        Args:
            user_id: Администратор, который правит конфиг
            command: Новый конфиг и версия, с которой его правили

        Raises:
            ConfigMissingError: Конфиг ещё не записан
            ConfigVersionConflictError: Правили не последнюю версию, или её записали параллельно
        """
        async with self._uow.transaction():
            latest_media_config = await self._uow.media_config_repository.find_latest_media_config()
            if latest_media_config is None:
                raise ConfigMissingError(domain="media")

            version = next_config_version(
                latest_version=latest_media_config.version,
                edited_version=command.edited_version,
            )
            if command.snapshot == latest_media_config.snapshot:
                return

            await self._uow.media_config_repository.insert_media_config(
                version=version,
                snapshot=command.snapshot,
                created_by=user_id,
            )
            await self._uow.commit()


def _image_upload_rules(*, kind_rules: ImageKindRules, kind_spec: ImageKindSpec) -> ImageUploadRules:
    """
    Соединяет изменяемые правила вида-картинки с осью минимальной стороны из кода.

    Scenarios:
        - показ правил загрузки клиенту до выбора файла

    Args:
        kind_rules: Правила вида из конфига
        kind_spec: Неизменяемая спецификация того же вида

    Returns:
        Правила загрузки вида
    """
    return ImageUploadRules(
        max_size_bytes=kind_rules.max_size_bytes,
        formats=kind_rules.formats,
        min_side=kind_rules.min_side,
        min_side_axis=kind_spec.min_side_axis,
    )


def _video_upload_rules(kind_rules: VideoKindRules) -> VideoUploadRules:
    """
    Переводит изменяемые правила вида-видео в правила загрузки.

    Scenarios:
        - показ правил загрузки клиенту до выбора файла

    Args:
        kind_rules: Правила вида из конфига

    Returns:
        Правила загрузки вида
    """
    return VideoUploadRules(max_size_bytes=kind_rules.max_size_bytes, formats=kind_rules.formats)
