"""
api-тесты ``HTTPLoggingMiddleware`` на минимальном приложении (``middleware_app``).

Одна строка лога на запрос (``event="http.request"``): уровень — по ошибке, без неё — по статусу; тип и код
ошибки; трейсбек только у нашего сбоя; полный шаблон маршрута; номер запроса и пользователь. Ответ проходит без
изменений. Строки снимаются ``capture_logs`` с процессорами контекста запроса.
"""

import re
from collections.abc import Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient
from starlette.types import Message, Receive, Scope, Send
from structlog.testing import capture_logs
from structlog.typing import Processor

from app.shared.exceptions import InternalError
from app.shared.logging.middleware import HTTPLoggingMiddleware
from app.shared.schemas.base import BFastAPI

type MakeAsyncClient = Callable[[BFastAPI], AsyncClient]

_REQUEST_EVENT = "http.request"


async def test_success_logs_info_with_full_route_template_and_trace_id(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
) -> None:
    """2xx через роутер с префиксом: ответ без изменений; INFO с полным шаблоном маршрута, параметрами и номером."""
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/v1/items/7/", params={"view": "full"})

    assert response.status_code == 200
    assert response.json() == {"item_id": 7}
    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["log_level"] == "info"
    assert line["method"] == "GET"
    assert line["path"] == "/v1/items/7/"
    assert line["route"] == "/v1/items/{item_id}/"
    assert line["query_params"] == "view=full"
    assert line["status_code"] == 200
    assert re.fullmatch(r"[0-9a-f]{32}", line["trace_id"])


async def test_app_without_telemetry_logs_request_without_route_and_trace_id(
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
) -> None:
    """Без телеметрии span'а нет: строка запроса пишется, но без шаблона маршрута и номера запроса."""
    app = BFastAPI()
    app.add_middleware(HTTPLoggingMiddleware)

    @app.get("/ping")
    async def _ping() -> dict[str, str]:
        return {"status": "ok"}

    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(app) as client:
            response = await client.get("/ping")

    assert response.status_code == 200
    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["status_code"] == 200
    assert "route" not in line
    assert "trace_id" not in line


async def test_internal_error_logs_one_error_line_with_type_code_and_traceback(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
) -> None:
    """INTERNAL, превращённая хендлером в ответ 500: одна строка ERROR с типом, кодом, текстом и трейсбеком."""
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/internal-error")

    assert response.status_code == 500
    assert response.json()["code"] == "internal"
    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["log_level"] == "error"
    assert line["status_code"] == 500
    assert line["error_type"] == "InternalError"
    assert line["error_code"] == "internal"
    assert line["error_message"] == "storage exploded"
    assert isinstance(line["exc_info"], InternalError)


async def test_client_category_error_logs_warning_with_code_without_traceback(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
) -> None:
    """Ошибка клиентской категории (404): WARNING с типом и кодом, трейсбека нет."""
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/app-error")

    assert response.status_code == 404
    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["log_level"] == "warning"
    assert line["status_code"] == 404
    assert line["error_type"] == "NotFoundError"
    assert line["error_code"] == "not_found"
    assert line["exc_info"] is None


async def test_validation_error_logs_warning_with_code_and_without_client_input(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
) -> None:
    """Невалидное тело (422): WARNING с типом и кодом; текста ошибки с сырым вводом клиента в строке нет."""
    sent_password = "hunter2"
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.post("/validated", json={"password": sent_password})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["log_level"] == "warning"
    assert line["error_type"] == "RequestValidationError"
    assert line["error_code"] == "validation_error"
    assert "error_message" not in line
    assert sent_password not in str(line)


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_level", "expected_route"),
    [
        ("/client-error", 400, "warning", "/client-error"),
        ("/server-error", 500, "error", "/server-error"),
        ("/no-such-route", 404, "warning", None),
    ],
)
async def test_response_without_exception_takes_level_from_status(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
    path: str,
    expected_status: int,
    expected_level: str,
    expected_route: str | None,
) -> None:
    """Ответ без исключения (собран вручную или неизвестный путь): уровень по статусу, ошибки в строке нет."""
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get(path)

    assert response.status_code == expected_status
    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["log_level"] == expected_level
    assert line["status_code"] == expected_status
    assert line.get("route") == expected_route
    assert "error_type" not in line


async def test_unhandled_exception_logs_one_error_line_with_status_500(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
) -> None:
    """Исключение мимо всех хендлеров: клиенту 500, в лог — одна строка ERROR со статусом 500 и трейсбеком."""
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/unhandled")

    assert response.status_code == 500
    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["log_level"] == "error"
    assert line["status_code"] == 500
    assert line["error_type"] == "RuntimeError"
    assert isinstance(line["exc_info"], RuntimeError)


async def test_authenticated_request_binds_user_id_and_next_request_starts_clean(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
    mint_access_token: Callable[..., str],
) -> None:
    """user_id из токена — в строке запроса и во внутренней строке; следующий анонимный запрос его не наследует."""
    user_id = uuid4()
    token = mint_access_token(user_id=user_id)
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            authenticated = await client.get("/whoami/", headers={"Authorization": f"Bearer {token}"})
            anonymous = await client.get("/v1/items/1/")

    assert authenticated.status_code == 200
    assert anonymous.status_code == 200
    assert [entry["user_id"] for entry in logs if entry["event"] == "test.inner"] == [user_id]
    assert [entry.get("user_id") for entry in logs if entry["event"] == _REQUEST_EVENT] == [user_id, None]


async def test_incoming_traceparent_continues_its_trace(
    middleware_app: BFastAPI,
    make_async_client: MakeAsyncClient,
    request_log_processors: tuple[Processor, ...],
) -> None:
    """Входящий W3C traceparent продолжается: в строке его trace_id — на это опирается связка с трейсингом фронта."""
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    with capture_logs(processors=request_log_processors) as logs:
        async with make_async_client(middleware_app) as client:
            await client.get("/v1/items/1/", headers={"traceparent": f"00-{trace_id}-00f067aa0ba902b7-01"})

    (line,) = [entry for entry in logs if entry["event"] == _REQUEST_EVENT]
    assert line["trace_id"] == trace_id


async def test_non_http_scope_passes_through_without_request_line() -> None:
    """Не-HTTP вызов (старт приложения) проходит в приложение без изменений, строки запроса нет."""
    seen_scope_types: list[str] = []

    async def inner_app(scope: Scope, receive: Receive, send: Send) -> None:
        seen_scope_types.append(scope["type"])

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        return None

    with capture_logs() as logs:
        await HTTPLoggingMiddleware(inner_app)({"type": "lifespan"}, receive, send)

    assert seen_scope_types == ["lifespan"]
    assert logs == []
