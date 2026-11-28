from enum import StrEnum


class PermissionEnum(StrEnum):
    """
    Права, которые может нести access-токен: их выдаёт домен учётных записей, требуют маршруты.

    Значение — ``<домен>.<ресурс>.<действие>``, имя члена — то же значение заглавными через подчёркивание.
    """

    MEDIA_CONFIG_EDIT = "media.config.edit"
    AUTH_ACCOUNTS_READ = "auth.accounts.read"
    BACKOFFICE_ACCOUNTS_READ = "backoffice.accounts.read"
