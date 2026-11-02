"""
Базовый асинхронный HTTP-клиент на httpx.

Один экземпляр = один внешний сервис: владеет собственным httpx.AsyncClient
(пул соединений к конкретному base_url). Подклассы добавляют доменные методы
(например, send_email) поверх get/post/...; crosscutting в _request (маппинг
ошибок, лог) трогать не нужно.

Жизненный цикл клиента (создание/закрытие) живёт в отдельном *Component
обёртке поверх BaseComponent — здесь её намеренно нет, чтобы не смешивать роли.
"""

from http import HTTPMethod
from typing import Any

import httpx

from app.shared.infra.http.config import HTTPClientConfig
from app.shared.infra.http.exceptions import (
    ExternalAPIPersistentError,
    ExternalAPITemporaryError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)

# 502/503/504 — апстрим/гейтвей; 500 и 429 сознательно НЕ временные (см. exceptions.py)
_TEMPORARY_STATUSES: frozenset[int] = frozenset({502, 503, 504})


class BaseHTTPClient:
    """
    Базовый HTTP-клиент.

    Подклассы пробрасывают в __init__ свой HTTPClientConfig и добавляют доменные методы.
    Закрытие сетевых ресурсов — через aclose(); вызывает её *Component-обёртка в shutdown.
    """

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
        exc_class = (
            ExternalAPITemporaryError if response.status_code in _TEMPORARY_STATUSES else ExternalAPIPersistentError
        )
        bound_log.error(
            "http_client.error_response",
            status=response.status_code,
            error_message=message,
        )
        raise exc_class(
            method=method.value,
            url=str(response.request.url),
            status=response.status_code,
            message=message,
            body=body,
        )

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
