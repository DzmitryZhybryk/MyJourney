import datetime as dt
from typing import Annotated
from uuid import UUID

from pydantic import ConfigDict, Field

from app.media.domain.enums import ImageFormatEnum, VideoFormatEnum
from app.shared.schemas.base import CamelModel


class ImageKindRules(CamelModel):
    """Изменяемые правила вида-картинки: потолок размера, разрешённые форматы, минимальная сторона в пикселях."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_size_bytes: Annotated[int, Field(gt=0)]
    formats: Annotated[frozenset[ImageFormatEnum], Field(min_length=1)]
    min_side: Annotated[int, Field(gt=0)]


class VideoKindRules(CamelModel):
    """Изменяемые правила вида-видео: потолок размера и разрешённые форматы."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_size_bytes: Annotated[int, Field(gt=0)]
    formats: Annotated[frozenset[VideoFormatEnum], Field(min_length=1)]


class MediaConfigSnapshot(CamelModel):
    """Весь изменяемый конфиг media: по полю на каждый вид файла."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    avatar: ImageKindRules
    journey_photo: ImageKindRules
    journey_video: VideoKindRules


class AdminUpdateMediaConfigRequest(CamelModel):
    """Новый конфиг целиком и версия, с которой его правили: правка не последней версии — 409."""

    model_config = ConfigDict(extra="forbid")

    edited_version: Annotated[int, Field(ge=1)]
    snapshot: MediaConfigSnapshot


class SavedImageKindRules(CamelModel):
    """Сохранённые правила вида-картинки: только форма, без пределов формы правки."""

    model_config = ConfigDict(frozen=True)

    max_size_bytes: int
    formats: frozenset[ImageFormatEnum]
    min_side: int


class SavedVideoKindRules(CamelModel):
    """Сохранённые правила вида-видео: только форма, без пределов формы правки."""

    model_config = ConfigDict(frozen=True)

    max_size_bytes: int
    formats: frozenset[VideoFormatEnum]


class SavedMediaConfig(CamelModel):
    """Сохранённый конфиг media как он лежит в хранилище: по полю на каждый вид файла."""

    model_config = ConfigDict(frozen=True)

    avatar: SavedImageKindRules
    journey_photo: SavedImageKindRules
    journey_video: SavedVideoKindRules


class AdminMediaConfigResponse(CamelModel):
    """Последняя версия конфига: значения, номер версии, когда и кем записана (`createdBy` пуст у записи деплоя)."""

    model_config = ConfigDict(frozen=True)

    version: int
    snapshot: SavedMediaConfig
    created_at: dt.datetime
    created_by: UUID | None
