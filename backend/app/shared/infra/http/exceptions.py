"""
Исключения для внешних HTTP-клиентов.

Это инфраструктурные ошибки взаимодействия с внешними сервисами (Resend, провайдер-API
и т.п.). Они НЕ наследуют ``AppError`` и не имеют категории — 404 от внешнего API
не должен превращаться в HTTP 404 наружу (необработанными они дадут 500).
"""


class ExternalAPIError(Exception):
    """
    Базовое исключение при ошибке внешнего HTTP API.

    Содержит весь контекст вызова (метод, URL, статус, тело ответа), чтобы caller мог
    принимать решение, не обращаясь к raw httpx-объектам или подшитым атрибутам.
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
        super().__init__(message)
        self.method = method
        self.url = url
        self.status = status
        self.message = message
        self.body = body


class ExternalAPITemporaryError(ExternalAPIError):
    """
    Временная ошибка внешнего API: апстрим/гейтвей (502, 503, 504), таймаут, сетевая ошибка.

    Кандидат на повтор запроса. Сюда НЕ входит 429 (требует Retry-After и backoff —
    в этом классе caller'ом не обеспечивается) и 500 (часто детерминированный баг сервера).
    """


class ExternalAPIPersistentError(ExternalAPIError):
    """Постоянная ошибка внешнего API: 4xx (включая 429) и 500.

    Повторять без дополнительной координации (backoff, правки запроса) бессмысленно.
    """
