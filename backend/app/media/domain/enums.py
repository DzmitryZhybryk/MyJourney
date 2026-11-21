from enum import StrEnum


class ImageFormatEnum(StrEnum):
    """Форматы картинок, которые умеет обработка; какие из них разрешены сейчас — решает конфиг."""

    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"
    HEIC = "image/heic"
    HEIF = "image/heif"


class VideoFormatEnum(StrEnum):
    """Форматы видео, которые умеет обработка; какие из них разрешены сейчас — решает конфиг."""

    MP4 = "video/mp4"
    QUICKTIME = "video/quicktime"


class SideAxisEnum(StrEnum):
    """
    Какую сторону картинки сравнивают с минимальным размером вида.

    `SHORT` — для картинки, которую обрезают в квадрат: квадрат не больше короткой стороны, поэтому
    3000×400 при минимуме 512 не пройдёт. `LONG` — для картинки, которую показывают целиком: чёткость
    задаёт длинная сторона, поэтому узкая панорама 4000×600 при минимуме 1280 пройдёт.
    """

    SHORT = "short"
    LONG = "long"
