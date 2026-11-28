"""
Исключения для внешних HTTP-клиентов.

Сбой внешнего API для нашего клиента — всегда наш серверный сбой: временный (503) или постоянный
(500). Статус ответа провайдера в наш ответ не попадает — 404 от внешнего API не становится нашим 404.
"""

from datetime import timedelta

from app.shared.exceptions import AppError, InternalError, TemporaryError


class ExternalAPIError(AppError):
    """
    Маркер семьи сбоев внешнего HTTP API.

    Категории не задаёт: её даёт вторая база листа — `TemporaryError` или `InternalError`.
    Несёт контекст вызова (метод, URL, статус, тело ответа) для лога и для caller'а, которому
    нужно решение по конкретному сбою; наружу он не уходит.
    """

    def __init__(
        self,
        *,
        method: str,
        url: str,
        status: int | None,
        message: str,
        body: object | None = None,
    ) -> None:
        super().__init__(message=message)
        self.method = method
        self.url = url
        self.status = status
        self.body = body


class ExternalAPITemporaryError(ExternalAPIError, TemporaryError):
    """
    Временная ошибка внешнего API: любой 5xx, 429, 408, таймаут, сетевая ошибка — повтор позже может пройти.

    `retry_after` — срок из заголовка `Retry-After` ответа провайдера, `None`, если заголовка нет.
    """

    def __init__(
        self,
        *,
        method: str,
        url: str,
        status: int | None,
        message: str,
        body: object | None = None,
        retry_after: timedelta | None = None,
    ) -> None:
        super().__init__(method=method, url=url, status=status, message=message, body=body)
        # Конструктор ExternalAPIError передаёт по MRO в TemporaryError только message, поэтому срок ставится здесь.
        self.retry_after = retry_after


class ExternalAPIPersistentError(ExternalAPIError, InternalError):
    """Постоянная ошибка внешнего API: остальные 4xx — тот же запрос не пройдёт и при повторе."""
