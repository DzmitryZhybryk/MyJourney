from app.shared.exceptions import AppError, InternalError, TemporaryError


class ObjectStorageError(AppError):
    """
    Маркер семьи сбоев объектного хранилища: не ответило или отказало в операции.

    Сам не бросается и категории не задаёт: её даёт вторая база листа — `TemporaryError` или
    `InternalError`. Ловят его те, кому классификация сбоя не важна.
    """


class ObjectStorageTemporaryError(ObjectStorageError, TemporaryError):
    """Сбой, который может пройти сам: сеть, таймаут, обрыв тела, перегрузка или внутренняя ошибка хранилища."""


class ObjectStoragePersistentError(ObjectStorageError, InternalError):
    """Сбой, который повтор не исправит: нет прав, неверные ключи или подпись, нет бакета, ошибка запроса."""


class ObjectNotFoundError(InternalError):
    """
    Объекта по ключу нет в бакете.

    Технический сигнал хранилища, не ответ клиенту: вызывающий use case сам решает, что значит
    пропавший объект для его потока.
    """

    code = "media.object_not_found"
    message = "Файл не найден в хранилище"


class ObjectTooLargeError(InternalError):
    """Объект в бакете больше предела, с которым его читают."""

    code = "media.object_too_large"
    message = "Файл в хранилище больше допустимого"
