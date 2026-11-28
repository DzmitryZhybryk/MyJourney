from dataclasses import dataclass
from typing import Final

from app.media.domain.enums import SideAxisEnum

__all__ = ["AVATAR_SPEC", "JOURNEY_PHOTO_SPEC", "ImageKindSpec"]


@dataclass(frozen=True, slots=True)
class ImageKindSpec:
    """Неизменяемая часть правил вида-картинки: от неё зависят уже сохранённые объекты, поэтому она в коде."""

    min_side_axis: SideAxisEnum


AVATAR_SPEC: Final[ImageKindSpec] = ImageKindSpec(SideAxisEnum.SHORT)
JOURNEY_PHOTO_SPEC: Final[ImageKindSpec] = ImageKindSpec(SideAxisEnum.LONG)
