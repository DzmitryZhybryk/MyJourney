"""
Юнит-тесты страховочных веток exception-handler'ов.

Боевой путь (AppError → свой handler → envelope; исключение вне AppError → 500) и передача ошибки в строку лога
запроса покрыты api-тестами. Здесь — две защитные ветки, до которых через приложение не дойти: handler вызван
напрямую с «не тем» типом исключения. Нарушение инварианта: его данные не уходят клиенту. И тело ответа на
серверный сбой: сообщение и детали экземпляра остаются в логе.
"""

import json

import pytest
from starlette.requests import Request

from app.shared.exceptions.base import (
    AppError,
    InternalError,
    InvariantViolationError,
    NotFoundError,
    TemporaryError,
)
from app.shared.exceptions.handlers import app_error_handler, global_exception_handler


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code", "expected_message"),
    [
        (
            TemporaryError(message="S3 503 for u1/f1", details={"key": "u1/f1"}),
            503,
            "temporary",
            TemporaryError.message,
        ),
        (InternalError(message="pool exhausted", details={"pool": "db"}), 500, "internal", InternalError.message),
    ],
)
def test_app_error_handler_server_fault_hides_instance_message_and_details(
    bare_request: Request, error: AppError, expected_status: int, expected_code: str, expected_message: str
) -> None:
    """Серверный сбой отдаёт code и сообщение класса, без details и сообщения экземпляра."""
    response = app_error_handler(bare_request, error)

    body = json.loads(bytes(response.body))
    assert response.status_code == expected_status
    assert (body["code"], body["message"], body["details"]) == (expected_code, expected_message, None)


def test_app_error_handler_client_error_keeps_instance_message_and_details(bare_request: Request) -> None:
    """Ошибка запроса отдаёт сообщение и детали экземпляра: по details.field фронт подсвечивает поле."""
    response = app_error_handler(bare_request, NotFoundError(message="Поездка не найдена", details={"field": "id"}))

    body = json.loads(bytes(response.body))
    assert response.status_code == 404
    assert (body["message"], body["details"]) == ("Поездка не найдена", {"field": "id"})


def test_app_error_handler_with_non_app_error_returns_internal(bare_request: Request) -> None:
    """app_error_handler с исключением вне AppError → 500 {code: internal} (страховка)."""
    response = app_error_handler(bare_request, ValueError("boom"))

    assert response.status_code == 500
    assert json.loads(bytes(response.body)) == {"code": "internal", "message": "Внутренняя ошибка сервера"}


def test_global_handler_delegates_app_error_to_envelope(bare_request: Request) -> None:
    """global_exception_handler с AppError делегирует app_error_handler (статус по категории)."""
    response = global_exception_handler(bare_request, NotFoundError())

    assert response.status_code == 404
    assert json.loads(bytes(response.body))["code"] == "not_found"


def test_global_handler_with_invariant_violation_returns_internal_without_context(bare_request: Request) -> None:
    """Нарушение инварианта → 500 {code: internal}, данные из сообщения клиенту не уходят."""
    response = global_exception_handler(bare_request, InvariantViolationError(key="secret-key"))

    assert response.status_code == 500
    assert json.loads(bytes(response.body)) == {"code": "internal", "message": "Внутренняя ошибка сервера"}
