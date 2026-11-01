"""
Фикстуры api-тестов shared-инфры.

``middleware_app`` — минимальное ASGI-приложение с навешенным ``HTTPLoggingMiddleware``
и роутами под каждый класс исхода (2xx / 4xx-response / 5xx-response / необработанное
исключение). Имена роутов заданы явно — middleware выводит из них имя события.
"""

import pytest
from fastapi.responses import JSONResponse

from app.shared.exceptions import NotFoundError
from app.shared.logging.middleware import HTTPLoggingMiddleware
from app.shared.schemas.base import BFastAPI


@pytest.fixture
def middleware_app() -> BFastAPI:
    """ASGI-приложение с ``HTTPLoggingMiddleware`` и роутами на каждый класс статуса/исключение."""
    app = BFastAPI()
    app.add_middleware(HTTPLoggingMiddleware)

    @app.get("/ok", name="ok_handler")
    async def _ok() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/client-error", name="client_error_handler")
    async def _client_error() -> JSONResponse:
        return JSONResponse({"error": "bad request"}, status_code=400)

    @app.get("/server-error", name="server_error_handler")
    async def _server_error() -> JSONResponse:
        return JSONResponse({"error": "boom"}, status_code=500)

    @app.get("/unhandled", name="unhandled_handler")
    async def _unhandled() -> JSONResponse:
        raise RuntimeError("unhandled failure")  # noqa: TRY003 — намеренный сбой роута для except-ветки

    # Без register_exception_handlers AppError НЕ конвертируется в Response, а доходит
    # до middleware как исключение — это покрывает WARNING-ветку except (клиентская категория).
    @app.get("/app-error", name="app_error_route")
    async def _app_error() -> JSONResponse:
        raise NotFoundError

    return app
