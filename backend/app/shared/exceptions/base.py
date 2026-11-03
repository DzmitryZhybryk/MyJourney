"""Базовые исключения приложения."""

from enum import Enum
from typing import ClassVar

from app.shared.types import OptionalDict


class ErrorCategoryEnum(Enum):
    """
    Транспортно-нейтральная категория ошибки приложения.

    Бросающий код классифицирует род сбоя в собственных терминах и НЕ знает про HTTP,
    gRPC и прочие транспорты. Перевод категории в конкретный код транспорта —
    забота адаптера (HTTP-handler, будущий gRPC-handler и т.д.).
    """

    INVALID_INPUT = "invalid_input"
    UNAUTHENTICATED = "unauthenticated"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    GONE = "gone"
    UNPROCESSABLE = "unprocessable"
    RATE_LIMITED = "rate_limited"
    TEMPORARY = "temporary"
    INTERNAL = "internal"

    @property
    def is_server_fault(self) -> bool:
        """
        Сбой на нашей стороне, а не ошибка в запросе клиента.

        Scenarios:
            - ответ на ошибку через любой транспорт: у серверного сбоя наружу не уходят детали

        Returns:
            True для временного сбоя зависимости и внутренней ошибки
        """
        return self in {ErrorCategoryEnum.TEMPORARY, ErrorCategoryEnum.INTERNAL}


class AppError(Exception):
    """
    Базовое исключение для ошибок приложения, у которых есть категория.

    От него наследуются ошибки доменов и инфраструктурных адаптеров.
    Дочерние классы могут задать атрибуты класса `category`, `code` и `message`
    для дефолтных значений.

    Поле `category` несёт транспортно-нейтральный род ошибки (см. `ErrorCategoryEnum`):
    адаптер транспорта переводит его в свой код (HTTP-статус и т.п.).
    Поле `code` — стабильный машинно-читаемый идентификатор ошибки для клиента
    (часть API-контракта). Поле `details` несёт дополнительную метаинформацию
    (например, ``{"field": "email"}`` для подсветки конкретного поля формы);
    классовый дефолт для него наследники задают через `default_details` —
    отдельный ClassVar-канал, чтобы классовая константа не переопределяла
    инстанс-атрибут `details`.
    """

    category: ErrorCategoryEnum = ErrorCategoryEnum.INTERNAL
    code: str = "unknown_error"
    message: str = "Произошла ошибка"
    default_details: ClassVar[OptionalDict] = None

    def __init__(
        self,
        *,
        message: str | None = None,
        code: str | None = None,
        details: OptionalDict = None,
    ) -> None:
        if message is None:
            message = self.message

        if code is None:
            code = self.code

        if details is None:
            details = self.default_details

        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class InvalidInputError(AppError):
    """Базовое исключение для ошибок валидации и некорректного ввода."""

    category = ErrorCategoryEnum.INVALID_INPUT
    code = "invalid_input"
    message = "Некорректный запрос"


class UnauthenticatedError(AppError):
    """Базовое исключение для ошибок аутентификации."""

    category = ErrorCategoryEnum.UNAUTHENTICATED
    code = "unauthenticated"
    message = "Требуется авторизация"


class PermissionDeniedError(AppError):
    """Базовое исключение для ошибок доступа."""

    category = ErrorCategoryEnum.PERMISSION_DENIED
    code = "permission_denied"
    message = "Доступ запрещен"


class NotFoundError(AppError):
    """Базовое исключение для ошибок "ресурс не найден"."""

    category = ErrorCategoryEnum.NOT_FOUND
    code = "not_found"
    message = "Ресурс не найден"


class ConflictError(AppError):
    """Базовое исключение для конфликтов данных."""

    category = ErrorCategoryEnum.CONFLICT
    code = "conflict"
    message = "Конфликт данных"


class GoneError(AppError):
    """Базовое исключение для ресурсов, которые когда-то были и истекли."""

    category = ErrorCategoryEnum.GONE
    code = "gone"
    message = "Ресурс больше недоступен"


class UnprocessableError(AppError):
    """Базовое исключение для ошибок обработки корректно сформированной сущности."""

    category = ErrorCategoryEnum.UNPROCESSABLE
    code = "unprocessable"
    message = "Невозможно обработать запрос"


class RateLimitedError(AppError):
    """Базовое исключение для ошибок превышения лимита запросов."""

    category = ErrorCategoryEnum.RATE_LIMITED
    code = "rate_limited"
    message = "Превышен лимит запросов"


class TemporaryError(AppError):
    """
    Базовое исключение для временного сбоя зависимости: повтор той же операции позже может пройти.

    От него наследуется временный сбой любого внешнего вызова, постоянный — от `InternalError`.
    Фоновые задачи повторяются по этому классу, не перечисляя провайдеров.
    """

    category = ErrorCategoryEnum.TEMPORARY
    code = "temporary"
    message = "Не удалось выполнить запрос, повторите попытку позже"


class InternalError(AppError):
    """Базовое исключение для внутренних ошибок сервера."""

    category = ErrorCategoryEnum.INTERNAL
    code = "internal"
    message = "Внутренняя ошибка сервера"


class InvariantViolationError(Exception):
    """
    Наш код обнаружил, что его собственное допущение ложно.

    Корень вне дерева `AppError`: это не ответ клиенту, а повод для алерта и разбора, поэтому
    у него нет категории и `code`. Через HTTP он даёт общий 500, в лог — ERROR с трейсбеком.
    Наследник задаёт `message`; переданные именованные значения дописываются к нему в текст.
    """

    message: ClassVar[str] = "Нарушен инвариант"

    def __init__(self, **context: object) -> None:
        pairs = ", ".join(f"{name}={value!r}" for name, value in context.items())
        super().__init__(f"{self.message}: {pairs}" if pairs else self.message)
