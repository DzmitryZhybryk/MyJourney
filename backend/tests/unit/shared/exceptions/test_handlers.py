"""
Юнит-тесты страховочных веток exception-handler'ов.

Боевой путь (AppError → свой handler → envelope; исключение вне AppError → 500) и передача ошибки в строку лога
запроса покрыты api-тестами. Здесь — две защитные ветки, до которых через приложение не дойти: handler вызван
напрямую с «не тем» типом исключения. И нарушение инварианта: его данные не уходят клиенту.
"""

import json

from starlette.requests import Request

from app.shared.exceptions.base import InvariantViolationError, NotFoundError
from app.shared.exceptions.handlers import app_error_handler, global_exception_handler


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
