from collections.abc import Collection
from typing import Protocol

__all__ = ["BaseObjectStoragePort"]


class BaseObjectStoragePort(Protocol):
    """Общее для бакетов media: удаление объектов по ключам."""

    async def delete_objects(self, keys: Collection[str]) -> None:
        """
        Удаляет объекты по ключам; отсутствующий ключ ошибкой не считается.

        Scenarios:
            - уборка загрузок, так и не дошедших до обработки
            - удаление всех файлов аккаунта

        Args:
            keys: Ключи объектов

        Raises:
            ObjectStorageError: Хранилище отказало целиком или не удалило часть ключей
        """
        ...
