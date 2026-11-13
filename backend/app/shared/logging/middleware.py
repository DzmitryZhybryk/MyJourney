"""Middleware, которое пишет одну строку лога на каждый HTTP-запрос."""

import logging
import time
from dataclasses import dataclass
from http import HTTPStatus

import structlog
from fastapi.exceptions import RequestValidationError
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.semconv.attributes.http_attributes import HTTP_ROUTE
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.shared.exceptions import AppError
from app.shared.logging.classify import get_log_level_for_exception, get_log_level_for_status
from app.shared.logging.config import get_logger
from app.shared.types import DictStrAny

logger = get_logger(__name__)

_REQUEST_EVENT = "http.request"
_REQUEST_ERROR_KEY = "request_error"


@dataclass(frozen=True, slots=True)
class _RequestError:
    exc: Exception
    code: str | None


def remember_handled_error(*, request: Request, exc: Exception, code: str) -> None:
    """
    Оставляет для строки лога запроса ошибку, которую хендлер превратил в ответ.

    Хендлер отвечает клиенту раньше, чем запрос возвращается в middleware; без этой записи строка знала бы
    только статус ответа.

    Scenarios:
        - ответ на ошибку приложения
        - ответ на невалидный запрос

    Args:
        request: Запрос, на который хендлер отвечает
        exc: Исключение, превращённое в ответ
        code: Код ошибки, ушедший клиенту
    """
    request.scope.setdefault("state", {})[_REQUEST_ERROR_KEY] = _RequestError(exc=exc, code=code)


class HTTPLoggingMiddleware:
    """
    Пишет одну строку лога на каждый HTTP-запрос: метод, путь, шаблон маршрута, статус, время и ошибку.

    Чистый ASGI, а не ``BaseHTTPMiddleware``: тот запускает приложение отдельной задачей, и контекст лога,
    положенный глубже (``user_id`` при проверке токена), до строки запроса не доходит. Ошибку, которую хендлер
    уже превратил в ответ, берёт из ``remember_handled_error``; необработанное исключение пишет сам и пропускает
    дальше — ответ 500 строит внешний слой приложения.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()
        started_at = time.perf_counter()
        # Пока ответ не начался, клиент получит 500 от внешнего слоя: так кончаются и необработанное исключение,
        # и приложение, не отправившее ответ.
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR.value

        async def send_and_remember_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]

            await send(message)

        try:
            await self.app(scope, receive, send_and_remember_status)
        except Exception as exc:
            _log_request(
                scope=scope,
                status_code=status_code,
                error=_RequestError(exc=exc, code=None),
                started_at=started_at,
            )
            raise

        _log_request(
            scope=scope,
            status_code=status_code,
            error=scope.get("state", {}).get(_REQUEST_ERROR_KEY),
            started_at=started_at,
        )


def _log_request(*, scope: Scope, status_code: int, error: _RequestError | None, started_at: float) -> None:
    """
    Пишет строку лога запроса; уровень — по ошибке, а без неё — по статусу ответа.

    Scenarios:
        - каждый HTTP-запрос

    Args:
        scope: ASGI-scope запроса
        status_code: Статус, ушедший клиенту
        error: Ошибка, которой закончился запрос, если была
        started_at: Момент входа запроса в middleware (``time.perf_counter``)
    """
    fields: DictStrAny = {
        "method": scope["method"],
        "path": scope["path"],
        "status_code": status_code,
        "process_time": round(time.perf_counter() - started_at, 4),
    }
    if route_template := _get_route_template():
        fields["route"] = route_template

    if client := scope.get("client"):
        fields["client_ip"] = client[0]

    if query := scope.get("query_string"):
        fields["query_params"] = query.decode("latin-1")

    if error is None:
        logger.log(get_log_level_for_status(status_code), _REQUEST_EVENT, **fields)
        return

    fields["error_type"] = type(error.exc).__name__
    if error.code is not None:
        fields["error_code"] = error.code

    # pydantic хранит в ошибке валидации сырой ввод клиента, пароль в том числе, — её текст в лог не идёт.
    if not isinstance(error.exc, RequestValidationError):
        fields["error_message"] = str(error.exc)

    if isinstance(error.exc, AppError) and error.exc.details:
        fields["error_details"] = error.exc.details

    level = get_log_level_for_exception(error.exc)
    logger.log(level, _REQUEST_EVENT, exc_info=error.exc if level == logging.ERROR else None, **fields)


def _get_route_template() -> str | None:
    """
    Возвращает полный шаблон пути совпавшего маршрута (``/v1/journeys/{journey_id}/``).

    Маршрут из ``scope`` знает только свой путь внутри подключённого роутера, без префикса; полный шаблон
    FastAPI пишет в span запроса атрибутом ``http.route``.

    Scenarios:
        - строка лога запроса: поле ``route``

    Returns:
        Шаблон пути или ``None``, если маршрут не совпал или span'а запроса нет
    """
    span = trace.get_current_span()
    if not isinstance(span, ReadableSpan) or span.attributes is None:
        return None

    route_template = span.attributes.get(HTTP_ROUTE)
    return route_template if isinstance(route_template, str) else None
