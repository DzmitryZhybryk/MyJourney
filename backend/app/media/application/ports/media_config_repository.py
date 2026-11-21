import datetime as dt
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.media.domain.enums import ImageFormatEnum, VideoFormatEnum

__all__ = [
    "ImageKindRules",
    "MediaConfigRepositoryPort",
    "MediaConfigSnapshot",
    "StoredMediaConfig",
    "VideoKindRules",
]


class ImageKindRules(BaseModel):
    """
    Изменяемые правила загрузки вида-картинки.

    Только форма: пределы значений проверяет схема того, кто пишет конфиг. Лишние ключи игнорируются —
    снапшот, сохранённый до удаления поля, читается без ошибки.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    max_size_bytes: int
    formats: frozenset[ImageFormatEnum]
    min_side: int


class VideoKindRules(BaseModel):
    """
    Изменяемые правила загрузки вида-видео.

    Только форма: пределы значений проверяет схема того, кто пишет конфиг. Лишние ключи игнорируются —
    снапшот, сохранённый до удаления поля, читается без ошибки.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    max_size_bytes: int
    formats: frozenset[VideoFormatEnum]


class MediaConfigSnapshot(BaseModel):
    """Весь изменяемый конфиг media одной версии: по полю на каждый вид файла."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    avatar: ImageKindRules
    journey_photo: ImageKindRules
    journey_video: VideoKindRules


@dataclass(frozen=True, slots=True)
class StoredMediaConfig:
    """Версия конфига, как она записана: сам снапшот, номер, когда и кем."""

    version: int
    snapshot: MediaConfigSnapshot
    created_at: dt.datetime
    created_by: UUID | None


class MediaConfigRepositoryPort(Protocol):
    """Версии конфига media: строки только добавляются, текущая — с наибольшим номером."""

    async def find_latest_media_config(self) -> StoredMediaConfig | None:
        """
        Находит последнюю версию конфига.

        Scenarios:
            - показ правил загрузки клиенту до выбора файла
            - начальное значение при развёртывании: есть ли уже конфиг

        Returns:
            Последняя версия; ``None``, если конфиг ещё не записан
        """
        ...

    async def insert_media_config(
        self, *, version: int, snapshot: MediaConfigSnapshot, created_by: UUID | None
    ) -> None:
        """
        Записывает новую версию конфига.

        Scenarios:
            - начальное значение при развёртывании
            - правка конфига администратором

        Args:
            version: Номер новой версии
            snapshot: Весь конфиг
            created_by: Аккаунт, правивший конфиг; ``None`` — запись развёртыванием

        Raises:
            ConfigVersionConflictError: Версия с таким номером уже есть
        """
        ...
