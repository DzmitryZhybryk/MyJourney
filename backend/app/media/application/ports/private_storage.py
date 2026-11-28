import datetime as dt
from dataclasses import dataclass
from typing import Protocol

from app.media.application.ports.base_object_storage import BaseObjectStoragePort

__all__ = ["ObjectInfo", "PrivateStoragePort", "SignedUpload"]


@dataclass(frozen=True, slots=True)
class SignedUpload:
    """
    Подписанная ссылка на запись одного объекта для того, у кого нет ключей хранилища.

    `required_headers` вошли в подпись: писатель обязан прислать их на PUT ровно такими, иначе
    хранилище отвергнет запрос. Content-Length тоже подписан, но его браузер ставит сам.
    """

    url: str
    expires_at: dt.datetime
    required_headers: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ObjectInfo:
    """Что хранилище сообщает о записанном объекте, не отдавая его содержимого."""

    size_bytes: int
    content_type: str | None


class PrivateStoragePort(BaseObjectStoragePort, Protocol):
    """
    Приватный бакет: браузер кладёт в него оригиналы по подписанной ссылке, читает только бэкенд.

    Анонимного чтения у бакета нет, поэтому сюда можно класть то, что нельзя показывать.
    """

    async def sign_upload(
        self,
        *,
        key: str,
        content_type: str,
        size_bytes: int,
        expires_in: dt.timedelta,
    ) -> SignedUpload:
        """
        Подписывает ссылку, по которой браузер один раз положит объект по ключу.

        В подпись входят тип, точный размер и запрет перезаписи (`If-None-Match: *`): повтор по
        той же ссылке после успешной записи получает 412, а не затирает объект. Сеть не нужна —
        подпись считается локально.

        Scenarios:
            - выдача ссылки на загрузку файла
            - переподпись ссылки на тот же ключ, когда прежняя истекла

        Args:
            key: Ключ будущего объекта
            content_type: Тип содержимого, который писатель обязан прислать
            size_bytes: Точный размер тела в байтах
            expires_in: Сколько ссылка остаётся действительной

        Returns:
            Ссылка, момент её истечения и заголовки, обязательные на PUT

        Raises:
            ObjectStorageError: Подпись не удалось построить
        """
        ...

    async def head_object(self, key: str) -> ObjectInfo | None:
        """
        Сообщает размер и тип объекта, не читая его.

        Хранилищу не доверяют исполнение подписанного размера, поэтому записанное перепроверяется
        этим запросом.

        Scenarios:
            - подтверждение загрузки: записанное сверяется с заявленным, в том числе после повтора,
              получившего 412

        Args:
            key: Ключ объекта

        Returns:
            Размер и тип; `None`, если объекта нет

        Raises:
            ObjectStorageError: Хранилище отказало, в том числе в доступе, или не ответило
        """
        ...

    async def get_object(self, *, key: str, max_bytes: int) -> bytes:
        """
        Читает объект целиком, но не больше предела.

        Размер сверяется с пределом до чтения тела: слишком большой объект не скачивается вовсе.
        Предел страхует память читающего процесса, даже если записанное не было перепроверено.

        Scenarios:
            - фоновая обработка загруженной картинки

        Args:
            key: Ключ объекта
            max_bytes: Наибольший допустимый размер в байтах

        Returns:
            Содержимое объекта

        Raises:
            ObjectNotFoundError: Объекта нет
            ObjectTooLargeError: Объект больше `max_bytes`
            ObjectStorageError: Хранилище отказало или не ответило
        """
        ...
