"""
Базовый асинхронный HTTP-клиент на httpx.

Один экземпляр = один внешний сервис: владеет собственным httpx.AsyncClient
(пул соединений к конкретному base_url). Подклассы добавляют доменные методы
(например, send_email) поверх get/post/...; crosscutting в _request (маппинг
ошибок, лог) трогать не нужно.

Жизненный цикл клиента (создание/закрытие) живёт в отдельном *Component
обёртке поверх BaseComponent — здесь её намеренно нет, чтобы не смешивать роли.
"""

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from http import HTTPMethod, HTTPStatus
from typing import Any, ClassVar

import httpx

from app.shared.infra.http.config import HTTPClientConfig
from app.shared.infra.http.exceptions import (
    ExternalAPIPersistentError,
    ExternalAPITemporaryError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class BaseHTTPClient:
    """
    Базовый HTTP-клиент.

    Подклассы пробрасывают в __init__ свой HTTPClientConfig и добавляют доменные методы.
    Закрытие сетевых ресурсов — через aclose(); вызывает её *Component-обёртка в shutdown.
    Провайдер, у которого «повторите» означает ещё какой-то 4xx, переопределяет
    `_TEMPORARY_CLIENT_ERROR_STATUSES`; любой 5xx временный всегда.
    Срок повтора берётся из стандартного заголовка `Retry-After`; провайдер, который сообщает его иначе
    (другой заголовок, тело ответа), переопределяет `_retry_after`.
    """

    _TEMPORARY_CLIENT_ERROR_STATUSES: ClassVar[frozenset[HTTPStatus]] = frozenset(
        {HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.TOO_MANY_REQUESTS}
    )

    def __init__(self, *, config: HTTPClientConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=config.headers,
            limits=httpx.Limits(
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_keepalive_connections,
            ),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self._request(method=HTTPMethod.GET, endpoint=endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        return await self._request(method=HTTPMethod.POST, endpoint=endpoint, **kwargs)

    async def _request(self, *, method: HTTPMethod, endpoint: str, **kwargs: Any) -> httpx.Response:
        bound_log = logger.bind(method=method.value, endpoint=endpoint, base_url=self._config.base_url)
        try:
            response = await self._client.request(method=method.value, url=endpoint, **kwargs)
        except httpx.TimeoutException as err:
            bound_log.warning("http_client.timeout", error=str(err))
            raise ExternalAPITemporaryError(
                method=method.value,
                url=f"{self._config.base_url}{endpoint}",
                status=None,
                message="Запрос ко внешнему API завершился по таймауту",
            ) from err
        except httpx.RequestError as err:
            bound_log.warning("http_client.network_error", error=str(err))
            raise ExternalAPITemporaryError(
                method=method.value,
                url=f"{self._config.base_url}{endpoint}",
                status=None,
                message=f"Сетевая ошибка при вызове внешнего API: {err}",
            ) from err

        if response.is_success:
            bound_log.debug("http_client.success", status=response.status_code)
            return response

        body = self._safe_parse_body(response)
        message = self._extract_error_message(body) or f"HTTP {response.status_code}"
        if self._is_temporary_status(response.status_code):
            bound_log.warning("http_client.error_response", status=response.status_code, error_message=message)
            raise ExternalAPITemporaryError(
                method=method.value,
                url=str(response.request.url),
                status=response.status_code,
                message=message,
                body=body,
                retry_after=self._retry_after(response),
            )

        bound_log.error("http_client.error_response", status=response.status_code, error_message=message)
        raise ExternalAPIPersistentError(
            method=method.value,
            url=str(response.request.url),
            status=response.status_code,
            message=message,
            body=body,
        )

    def _retry_after(self, response: httpx.Response) -> timedelta | None:
        """
        Достаёт из ответа с временной ошибкой срок, через который провайдер просит повторить.

        Scenarios:
            - временный сбой внешнего API, в ответе которого провайдер сказал, когда повторить

        Args:
            response: Ответ провайдера с временной ошибкой

        Returns:
            Срок до повтора или `None`, если провайдер его не сообщил
        """
        return self._parse_retry_after(value=response.headers.get("Retry-After"), now=datetime.now(tz=UTC))

    @classmethod
    def _is_temporary_status(cls, status_code: int) -> bool:
        return status_code >= HTTPStatus.INTERNAL_SERVER_ERROR or status_code in cls._TEMPORARY_CLIENT_ERROR_STATUSES

    @staticmethod
    def _safe_parse_body(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            text = response.text
            return text or None

    @staticmethod
    def _extract_error_message(body: Any) -> str | None:
        if not isinstance(body, dict):
            return None

        for key in ("message", "detail", "error"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value

        return None

    @staticmethod
    def _parse_retry_after(*, value: str | None, now: datetime) -> timedelta | None:
        """
        Разбирает значение в формате `Retry-After`: число секунд или HTTP-дата.

        Нечитаемое значение — то же, что отсутствие заголовка: подсказка провайдера не должна ломать обработку его
        ошибки. Дата в прошлом даёт нулевой срок.

        Scenarios:
            - временный сбой внешнего API, в ответе которого провайдер сказал, когда повторить
            - провайдер, который шлёт срок в этом формате, но в своём заголовке

        Args:
            value: Значение заголовка или `None`, если его нет
            now: Текущий момент, от которого отсчитывается срок до HTTP-даты

        Returns:
            Срок до повтора или `None`, если значения нет или его не разобрать
        """
        if value is None:
            return None

        value = value.strip()
        if value.isdigit():
            return timedelta(seconds=int(value))

        try:
            retry_at = parsedate_to_datetime(value)
        except TypeError, ValueError:
            return None

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)

        return max(retry_at - now, timedelta(0))
