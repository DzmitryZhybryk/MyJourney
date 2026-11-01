"""
Unit-тесты сборки контекста логирования (``app.shared.logging.context``).

Чистые функции над ``Request``: извлечение клиентского контекста, сборка контекста
запроса (с явным контекстом и с фоллбэком на извлечённый) и контекста ошибки
(AppError без traceback'а vs неожиданная — с traceback'ом).
"""

from collections.abc import Callable

from starlette.requests import Request

from app.shared.exceptions import NotFoundError
from app.shared.logging.context import (
    build_error_log_context,
    build_log_context,
    extract_request_context,
)


def test_extract_request_context_collects_all_present_fields(make_request: Callable[..., Request]) -> None:
    """Контекст собирает client_ip, query_params и user_id/request_id из request.state."""
    request = make_request(
        client=("203.0.113.5", 54321),
        query=b"a=1&b=2",
        state={"user_id": "user-1", "request_id": "req-1"},
    )

    context = extract_request_context(request)

    assert context == {
        "client_ip": "203.0.113.5",
        "query_params": "a=1&b=2",
        "user_id": "user-1",
        "request_id": "req-1",
    }


def test_extract_request_context_empty_when_nothing_present(make_request: Callable[..., Request]) -> None:
    """Без client/query/state контекст пустой (опциональные поля не выдумываются)."""
    context = extract_request_context(make_request())

    assert context == {}


def test_build_log_context_uses_explicit_context_when_given(make_request: Callable[..., Request]) -> None:
    """При переданном ``context`` он подмешивается как есть (без извлечения из request)."""
    log_context = build_log_context(
        request=make_request(),
        status_code=200,
        process_time=0.12345,
        context={"trace": "abc"},
    )

    assert log_context["method"] == "GET"
    assert log_context["path"] == "/v1/ping"
    assert log_context["status_code"] == 200
    assert log_context["process_time"] == 0.1235
    assert log_context["trace"] == "abc"


def test_build_log_context_falls_back_to_extracted_context(make_request: Callable[..., Request]) -> None:
    """Без явного ``context`` подмешивается извлечённый из request (client_ip и т.п.)."""
    request = make_request(client=("203.0.113.5", 54321))

    log_context = build_log_context(request=request, status_code=200, process_time=0.1)

    assert log_context["client_ip"] == "203.0.113.5"


def test_build_error_log_context_for_app_error_omits_traceback(make_request: Callable[..., Request]) -> None:
    """AppError: пишутся error_code/error_message, traceback не нужен, статус из категории."""
    log_context, status_code, include_traceback = build_error_log_context(
        request=make_request(),
        exc=NotFoundError(),
        process_time=0.1,
    )

    assert status_code == 404
    assert log_context["error_code"] == "not_found"
    assert log_context["error_type"] == "NotFoundError"
    assert include_traceback is False


def test_build_error_log_context_for_unexpected_error_includes_traceback(make_request: Callable[..., Request]) -> None:
    """Неожиданная ошибка: error_message из str(exc), traceback включается."""
    log_context, status_code, include_traceback = build_error_log_context(
        request=make_request(),
        exc=ValueError("boom"),
        process_time=0.1,
    )

    assert status_code == 500
    assert log_context["error_message"] == "boom"
    assert include_traceback is True
