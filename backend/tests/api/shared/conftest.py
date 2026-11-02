"""
Фикстуры api-тестов shared-инфры.

``middleware_app`` — минимальное приложение, собранное как боевое API: ``HTTPLoggingMiddleware``, хендлеры ошибок
и телеметрия, — с роутами под каждый исход запроса. Часть роутов подключена роутером с префиксом: маршрут внутри
роутера знает только свой кусок пути, а в строке лога шаблон должен быть полным.

``request_log_processors`` — процессоры, которые ``capture_logs`` прогоняет перед захватом: без них строка не
получит контекст запроса (``trace_id``, ``user_id``). Боевую цепочку целиком проверяют unit-тесты настройки логов.
"""

from typing import Annotated
from uuid import UUID

import pytest
import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from structlog.typing import Processor

from app.shared.exceptions import InternalError, NotFoundError
from app.shared.exceptions.handlers import register_exception_handlers
from app.shared.infra.jwt.dependency import current_user_id_dependency
from app.shared.infra.telemetry.tracing import get_api_telemetry_config
from app.shared.logging.context import add_trace_context
from app.shared.logging.middleware import HTTPLoggingMiddleware
from app.shared.schemas.base import BFastAPI


class _CredentialsRequest(BaseModel):
    password: str = Field(min_length=8)


@pytest.fixture
def middleware_app() -> BFastAPI:
    """Приложение с middleware логирования, хендлерами ошибок, телеметрией и роутами на каждый исход запроса."""
    app = BFastAPI(telemetry=get_api_telemetry_config())
    app.add_middleware(HTTPLoggingMiddleware)
    register_exception_handlers(app)

    items_router = APIRouter()

    @items_router.get("/{item_id}/")
    async def _get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    app.include_router(items_router, prefix="/v1/items")

    @app.get("/whoami/")
    async def _whoami(user_id: Annotated[UUID, Depends(current_user_id_dependency)]) -> dict[str, str]:
        structlog.get_logger("test.inner").info("test.inner")
        return {"user_id": str(user_id)}

    @app.get("/client-error")
    async def _client_error() -> JSONResponse:
        return JSONResponse({"error": "bad request"}, status_code=400)

    @app.get("/server-error")
    async def _server_error() -> JSONResponse:
        return JSONResponse({"error": "boom"}, status_code=500)

    @app.get("/app-error")
    async def _app_error() -> JSONResponse:
        raise NotFoundError

    @app.get("/internal-error")
    async def _internal_error() -> JSONResponse:
        raise InternalError(message="storage exploded")

    @app.post("/validated")
    async def _validated(body: _CredentialsRequest) -> dict[str, int]:
        return {"length": len(body.password)}

    @app.get("/unhandled")
    async def _unhandled() -> JSONResponse:
        raise RuntimeError("unhandled failure")  # noqa: TRY003 — намеренный сбой роута

    return app


@pytest.fixture
def request_log_processors() -> tuple[Processor, ...]:
    """Процессоры контекста запроса для ``capture_logs``: значения, привязанные к запросу, и его номер."""
    return (structlog.contextvars.merge_contextvars, add_trace_context)
