from enum import StrEnum


class PermissionEnum(StrEnum):
    """Права, которые может нести access-токен: их выдаёт домен учётных записей, требуют маршруты."""

    MEDIA_CONFIG_EDIT = "media.config.edit"
