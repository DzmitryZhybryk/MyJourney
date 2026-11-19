"""
api-тест сборки боевого приложения (``create_app``): строка лога запроса получает номер и шаблон маршрута.

Остальные тесты логирования строят своё приложение; этот ловит потерю телеметрии или middleware в самом
``create_app``. ``/healthz/`` не трогает компоненты, поэтому запрос проходит без их старта.
"""

import re
from collections.abc import Callable

import structlog
from httpx import AsyncClient
from structlog.testing import capture_logs

from app.shared.logging.context import add_trace_context
from app.shared.schemas.base import BFastAPI


async def test_production_app_logs_request_with_trace_id_and_route(
    production_app: BFastAPI,
    make_async_client: Callable[[BFastAPI], AsyncClient],
) -> None:
    """Запрос к боевому приложению — одна строка ``http.request`` с номером запроса и шаблоном маршрута."""
    with capture_logs(processors=[structlog.contextvars.merge_contextvars, add_trace_context]) as logs:
        async with make_async_client(production_app) as client:
            response = await client.get("/healthz/")

    assert response.status_code == 200
    (line,) = [entry for entry in logs if entry["event"] == "http.request"]
    assert line["route"] == "/healthz/"
    assert re.fullmatch(r"[0-9a-f]{32}", line["trace_id"])
