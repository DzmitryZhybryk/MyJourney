"""
Глобальные обработчики исключений для приложения.

Преобразуют исключения приложения в HTTP ответы, не привязываясь к конкретному
presentation фреймворку (FastAPI, gRPC и т.д.).
"""

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.exceptions import AppError
from app.shared.exceptions.mappings import resolve_http_status
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.logging.middleware import remember_handled_error

type ExceptionHandlerT = Callable[[Request, Any], JSONResponse]

# Ответ на исключение вне AppError / необработанное исключение: наружу не утекают детали внутренней ошибки.
_INTERNAL_ERROR_CONTENT = {"code": "internal", "message": "Внутренняя ошибка сервера"}
_VALIDATION_ERROR_CODE = "validation_error"


def _create_error_response(exc: AppError) -> JSONResponse:
    """
    Создает HTTP ответ для исключения приложения используя типизированную схему.

    Scenarios:
        - любой запрос, завершившийся ошибкой приложения
    """
    error_response = ErrorResponse(code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(
        status_code=resolve_http_status(exc),
        content=error_response.model_dump(mode="json"),
    )


def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обрабатывает исключения приложения, преобразуя их в HTTP ответы.

    Scenarios:
        - любой запрос, завершившийся ошибкой приложения
    """
    # Handler зарегистрирован на AppError, поэтому exc гарантированно AppError; HTTP-статус и тело берём
    # прямо из исключения через единый resolve_http_status.
    if isinstance(exc, AppError):
        remember_handled_error(request=request, exc=exc, code=exc.code)
        return _create_error_response(exc)

    # Страховка на случай прямого вызова с исключением вне AppError.
    return JSONResponse(status_code=500, content=_INTERNAL_ERROR_CONTENT)


def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Преобразует ошибки валидации FastAPI/pydantic (422) в единый ErrorResponse.

    По умолчанию FastAPI отдаёт 422 в формате ``{"detail": [...]}`` без поля
    ``code``, что ломает контракт ошибки на клиенте. Здесь 422 заворачивается в
    тот же envelope, что и ошибки приложения: ``code="validation_error"`` плюс
    ``details`` со списком проблемных полей (берём из ``loc``/``msg`` только
    строки, чтобы тело гарантированно сериализовалось в JSON).

    Scenarios:
        - любой запрос, не прошедший валидацию тела или параметров

    Args:
        request: HTTP-запрос, на который отвечаем
        exc: Исключение валидации pydantic с детализацией по полям

    Returns:
        JSON-ответ 422 в формате ErrorResponse
    """
    fields = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "reason": error["msg"],
        }
        for error in exc.errors()
    ]

    error_response = ErrorResponse(
        code=_VALIDATION_ERROR_CODE,
        message="Переданы некорректные данные",
        details={"fields": fields},
    )
    remember_handled_error(request=request, exc=exc, code=_VALIDATION_ERROR_CODE)

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode="json"),
    )


def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обрабатывает необработанные исключения (вне AppError → 500).

    Scenarios:
        - любой запрос, упавший с необработанным исключением
    """
    # Страховка на случай прямого вызова с AppError: через приложение
    # AppError уходит в свой app_error_handler и сюда не доходит.
    if isinstance(exc, AppError):
        return app_error_handler(request, exc)

    # Лог здесь не пишем: исключение проходит сквозь middleware логирования, и строку с трейсбеком пишет оно.
    return JSONResponse(status_code=500, content=_INTERNAL_ERROR_CONTENT)


BASE_EXCEPTION_HANDLERS: dict[type[Exception], ExceptionHandlerT] = {
    # AppError регистрируем явно, чтобы Starlette положил handler в ExceptionMiddleware (внутренний слой).
    # Иначе ошибку приложения поймает handler на Exception во внешнем ServerErrorMiddleware, а тот после ответа
    # поднимает исключение дальше, до сервера.
    AppError: app_error_handler,
    # RequestValidationError перехватываем явно, иначе FastAPI вернёт дефолтный
    # 422 {"detail": [...]} без поля code — в обход нашего ErrorResponse-контракта.
    RequestValidationError: validation_exception_handler,
    Exception: global_exception_handler,
}


def register_exception_handlers(app: FastAPI) -> None:
    """
    Регистрирует обработчики исключений для FastAPI приложения.

    Scenarios:
        - запуск API-приложения

    Args:
        app: Экземпляр FastAPI приложения
    """
    for exc_class, handler in BASE_EXCEPTION_HANDLERS.items():
        app.add_exception_handler(exc_class, handler)
