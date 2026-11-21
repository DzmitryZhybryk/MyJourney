import datetime as dt
from dataclasses import dataclass
from uuid import UUID

from app.media.application.ports.media_config_repository import MediaConfigSnapshot
from app.media.domain.enums import ImageFormatEnum, SideAxisEnum, VideoFormatEnum

__all__ = ["ImageUploadRules", "MediaConfigResult", "UploadRulesResult", "VideoUploadRules"]


@dataclass(frozen=True, slots=True)
class MediaConfigResult:
    """Версия конфига media для правки: сам конфиг, номер версии, когда и кем записана."""

    version: int
    snapshot: MediaConfigSnapshot
    created_at: dt.datetime
    created_by: UUID | None


@dataclass(frozen=True, slots=True)
class ImageUploadRules:
    """Правила загрузки вида-картинки: изменяемые из конфига и ось минимальной стороны из кода."""

    max_size_bytes: int
    formats: frozenset[ImageFormatEnum]
    min_side: int
    min_side_axis: SideAxisEnum


@dataclass(frozen=True, slots=True)
class VideoUploadRules:
    """Правила загрузки вида-видео."""

    max_size_bytes: int
    formats: frozenset[VideoFormatEnum]


@dataclass(frozen=True, slots=True)
class UploadRulesResult:
    """Правила загрузки по последней версии конфига: по полю на каждый вид файла."""

    avatar: ImageUploadRules
    journey_photo: ImageUploadRules
    journey_video: VideoUploadRules
