from pydantic import ConfigDict

from app.media.domain.enums import ImageFormatEnum, SideAxisEnum, VideoFormatEnum
from app.shared.schemas.base import CamelModel


class ImageUploadRules(CamelModel):
    """Правила загрузки вида-картинки; `minSideAxis` — какую сторону сравнивать с `minSide`."""

    model_config = ConfigDict(frozen=True)

    max_size_bytes: int
    formats: frozenset[ImageFormatEnum]
    min_side: int
    min_side_axis: SideAxisEnum


class VideoUploadRules(CamelModel):
    """Правила загрузки вида-видео."""

    model_config = ConfigDict(frozen=True)

    max_size_bytes: int
    formats: frozenset[VideoFormatEnum]


class UploadRulesResponse(CamelModel):
    """Текущие правила загрузки: по полю на каждый вид файла."""

    model_config = ConfigDict(frozen=True)

    avatar: ImageUploadRules
    journey_photo: ImageUploadRules
    journey_video: VideoUploadRules
