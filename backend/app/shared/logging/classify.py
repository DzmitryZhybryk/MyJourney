"""Уровень строки лога запроса: по исключению, которым закончился запрос, или по статусу ответа."""

import logging
from http import HTTPStatus

from fastapi.exceptions import RequestValidationError

from app.shared.exceptions import AppError, ErrorCategoryEnum


def get_log_level_for_exception(exc: Exception) -> int:
    """
    Определяет уровень лога по исключению, которым закончился запрос.

    Scenarios:
        - строка лога запроса, закончившегося ошибкой

    Args:
        exc: Исключение

    Returns:
        ``logging.ERROR`` для нашего сбоя (категория INTERNAL или исключение вне дерева ошибок),
        ``logging.WARNING`` для ошибки клиента (невалидный запрос, клиентские категории) и временного
        сбоя зависимости (TEMPORARY): это не наш баг, сигнал для алерта — доля таких ответов
    """
    if isinstance(exc, AppError):
        return logging.ERROR if exc.category is ErrorCategoryEnum.INTERNAL else logging.WARNING

    if isinstance(exc, RequestValidationError):
        return logging.WARNING

    return logging.ERROR


def get_log_level_for_status(status_code: int) -> int:
    """
    Определяет уровень лога по статусу ответа, когда запрос закончился без исключения.

    Scenarios:
        - строка лога запроса: 404 на неизвестный путь, 405, ответ с кодом ошибки, собранный вручную

    Args:
        status_code: HTTP-статус ответа

    Returns:
        ``logging.ERROR`` для 5xx, ``logging.WARNING`` для 4xx, иначе ``logging.INFO``
    """
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return logging.ERROR

    if status_code >= HTTPStatus.BAD_REQUEST:
        return logging.WARNING

    return logging.INFO
