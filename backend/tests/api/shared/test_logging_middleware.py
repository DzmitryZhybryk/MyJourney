"""
api-тесты ``HTTPLoggingMiddleware`` на минимальном ASGI-приложении.

Проверяют наблюдаемое поведение: middleware пробрасывает ответ/исключение без изменений
и логирует событие на уровне по классу исхода (2xx→info, 4xx→warning, 5xx→error,
необработанное исключение→error). Логи снимаются через ``structlog.testing.capture_logs``,
имя события выводится из ``route.name`` (``ok_handler`` → ``"Ok handler"``).
"""

from collections.abc import Callable

from httpx import AsyncClient
from structlog.testing import capture_logs

from app.shared.schemas.base import BFastAPI


async def test_success_passes_response_and_logs_info(
    middleware_app: BFastAPI,
    make_async_client: Callable[[BFastAPI], AsyncClient],
) -> None:
    """2xx: ответ проходит без изменений, событие логируется на уровне info."""
    with capture_logs() as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/ok")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    matching = [entry for entry in logs if entry.get("event") == "Ok handler"]
    assert len(matching) == 1
    assert matching[0]["log_level"] == "info"
    assert matching[0]["status_code"] == 200


async def test_client_error_response_logs_warning(
    middleware_app: BFastAPI,
    make_async_client: Callable[[BFastAPI], AsyncClient],
) -> None:
    """4xx-response: ответ проходит, событие логируется на уровне warning."""
    with capture_logs() as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/client-error")

    assert response.status_code == 400
    matching = [entry for entry in logs if entry.get("event") == "Client error handler"]
    assert len(matching) == 1
    assert matching[0]["log_level"] == "warning"


async def test_server_error_response_logs_error(
    middleware_app: BFastAPI,
    make_async_client: Callable[[BFastAPI], AsyncClient],
) -> None:
    """5xx-response: ответ проходит, событие логируется на уровне error."""
    with capture_logs() as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/server-error")

    assert response.status_code == 500
    matching = [entry for entry in logs if entry.get("event") == "Server error handler"]
    assert len(matching) == 1
    assert matching[0]["log_level"] == "error"


async def test_unhandled_exception_is_logged_and_reraised(
    middleware_app: BFastAPI,
    make_async_client: Callable[[BFastAPI], AsyncClient],
) -> None:
    """Необработанное исключение логируется на уровне error и пробрасывается (→ 500 наружу)."""
    with capture_logs() as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/unhandled")

    assert response.status_code == 500
    matching = [entry for entry in logs if entry.get("event") == "Unhandled handler"]
    assert len(matching) == 1
    assert matching[0]["log_level"] == "error"
    assert matching[0]["error_type"] == "RuntimeError"


async def test_warning_classified_exception_logs_warning(
    middleware_app: BFastAPI,
    make_async_client: Callable[[BFastAPI], AsyncClient],
) -> None:
    """AppError клиентской категории, дошедший как exception, логируется на уровне warning."""
    with capture_logs() as logs:
        async with make_async_client(middleware_app) as client:
            response = await client.get("/app-error")

    # без зарегистрированных хендлеров AppError доходит до ServerErrorMiddleware → 500
    assert response.status_code == 500
    matching = [entry for entry in logs if entry.get("event") == "App error route"]
    assert len(matching) == 1
    assert matching[0]["log_level"] == "warning"
