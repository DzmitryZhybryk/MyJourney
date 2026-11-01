"""Сборка контекста логирования для HTTP-запросов и ошибок."""

from starlette.requests import Request

from app.shared.exceptions import AppError
from app.shared.logging.classify import get_status_code_from_exception
from app.shared.types import DictStrAny


def extract_request_context(request: Request) -> DictStrAny:
    """
    Извлекает базовый контекст из HTTP запроса.

    Scenarios:
        - лог каждого HTTP-запроса

    Args:
        request: HTTP запрос

    Returns:
        Словарь с базовым контекстом запроса
    """
    context: DictStrAny = {}

    if request.client:
        context["client_ip"] = request.client.host

    if request.url.query:
        context["query_params"] = request.url.query

    if hasattr(request.state, "user_id"):
        context["user_id"] = str(request.state.user_id)

    if hasattr(request.state, "request_id"):
        context["request_id"] = str(request.state.request_id)

    return context


def build_log_context(
    *,
    request: Request,
    status_code: int,
    process_time: float,
    context: DictStrAny | None = None,
) -> DictStrAny:
    """
    Формирует полный контекст для логирования HTTP запроса.

    Scenarios:
        - лог каждого HTTP-запроса

    Args:
        request: HTTP запрос
        status_code: HTTP статус код ответа
        process_time: Время обработки запроса в секундах
        context: Дополнительный контекст (например, из extract_request_context)

    Returns:
        Полный контекст для логирования
    """
    log_context = {
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "process_time": round(process_time, 4),
    }

    if context:
        log_context.update(context)
    else:
        log_context.update(extract_request_context(request))

    return log_context


def build_error_log_context(
    *,
    request: Request,
    exc: Exception,
    process_time: float,
    context: DictStrAny | None = None,
) -> tuple[DictStrAny, int, bool]:
    """
    Формирует контекст для логирования ошибки и определяет параметры логирования.

    Scenarios:
        - лог HTTP-запроса, завершившегося исключением

    Args:
        request: HTTP запрос
        exc: Исключение
        process_time: Время обработки запроса в секундах
        context: Дополнительный контекст (например, из extract_request_context)

    Returns:
        Tuple из (контекст логирования, статус код, нужно ли включать traceback)
    """
    status_code = get_status_code_from_exception(exc)

    log_context = build_log_context(
        request=request,
        status_code=status_code,
        process_time=process_time,
        context=context,
    )

    log_context["error_type"] = type(exc).__name__

    if isinstance(exc, AppError):
        log_context["error_code"] = exc.code
        log_context["error_message"] = exc.message
        include_traceback = False
    else:
        log_context["error_message"] = str(exc)
        include_traceback = True

    return log_context, status_code, include_traceback
