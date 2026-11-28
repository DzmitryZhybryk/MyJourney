from typing import Protocol

from app.media.application.ports.base_object_storage import BaseObjectStoragePort

__all__ = ["PublicStoragePort"]


class PublicStoragePort(BaseObjectStoragePort, Protocol):
    """
    Публичный бакет: бэкенд пишет в него готовые к показу файлы, читают их анонимно по URL.

    Всё, что сюда попадает, видно любому, кто знает ключ.
    """

    async def put_object(self, *, key: str, body: bytes, content_type: str, cache_control: str) -> None:
        """
        Записывает объект по ключу.

        Scenarios:
            - фоновая обработка: запись готовых вариантов картинки

        Args:
            key: Ключ объекта
            body: Содержимое
            content_type: Тип содержимого, с которым объект будут читать
            cache_control: Заголовок `Cache-Control`, который хранилище отдаст читателю

        Raises:
            ObjectStorageError: Хранилище отказало или не ответило
        """
        ...
