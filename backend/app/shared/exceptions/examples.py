"""Утилиты для описания ошибок API."""

from app.shared.exceptions.base import AppError
from app.shared.types import DictStrAny


def error_response_example(error_cls: type[AppError]) -> DictStrAny:
    """
    Вернуть словарь для примера `ErrorResponse` по исключению.

    Scenarios:
        - примеры ошибок в OpenAPI: каждый домен описывает ими ответы своих эндпоинтов
    """

    return {
        "code": error_cls.code,
        "message": error_cls.message,
        "details": error_cls.default_details,
        "timestamp": "2024-01-01T12:00:00Z",
    }
