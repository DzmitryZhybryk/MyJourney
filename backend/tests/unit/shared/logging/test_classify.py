"""Unit-тесты уровня строки лога запроса: по исключению, которым закончился запрос, и по статусу ответа."""

import logging

import pytest
from fastapi.exceptions import RequestValidationError

from app.shared.exceptions.base import (
    AppError,
    ConflictError,
    ErrorCategoryEnum,
    GoneError,
    InternalError,
    InvalidInputError,
    InvariantViolationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    UnauthenticatedError,
    UnprocessableError,
)
from app.shared.logging.classify import get_log_level_for_exception, get_log_level_for_status

_LEVEL_BY_CATEGORY: tuple[tuple[AppError, int], ...] = (
    (InvalidInputError(), logging.WARNING),
    (UnauthenticatedError(), logging.WARNING),
    (PermissionDeniedError(), logging.WARNING),
    (NotFoundError(), logging.WARNING),
    (ConflictError(), logging.WARNING),
    (GoneError(), logging.WARNING),
    (UnprocessableError(), logging.WARNING),
    (RateLimitedError(), logging.WARNING),
    (InternalError(), logging.ERROR),
)


@pytest.mark.parametrize(("error", "expected_level"), _LEVEL_BY_CATEGORY)
def test_get_log_level_for_exception_maps_each_category(error: AppError, expected_level: int) -> None:
    """INTERNAL — наш сбой → ERROR; остальные категории — ошибка клиента → WARNING."""
    assert get_log_level_for_exception(error) == expected_level


def test_level_table_has_a_row_for_every_category() -> None:
    """У каждой категории есть строка в таблице уровней: новая категория без решения об уровне роняет тест."""
    assert {error.category for error, _ in _LEVEL_BY_CATEGORY} == set(ErrorCategoryEnum)


@pytest.mark.parametrize(
    ("error", "expected_level"),
    [
        (RequestValidationError([]), logging.WARNING),
        (InvariantViolationError(), logging.ERROR),
        (RuntimeError("boom"), logging.ERROR),
    ],
)
def test_get_log_level_for_exception_outside_categories(error: Exception, expected_level: int) -> None:
    """Невалидный запрос — ошибка клиента (WARNING); нарушенный инвариант и чужое исключение — наш сбой (ERROR)."""
    assert get_log_level_for_exception(error) == expected_level


@pytest.mark.parametrize(
    ("status_code", "expected_level"),
    [
        (200, logging.INFO),
        (307, logging.INFO),
        (399, logging.INFO),
        (400, logging.WARNING),
        (404, logging.WARNING),
        (499, logging.WARNING),
        (500, logging.ERROR),
        (503, logging.ERROR),
    ],
)
def test_get_log_level_for_status_by_status_class(status_code: int, expected_level: int) -> None:
    """Без исключения: 5xx → ERROR, 4xx → WARNING, остальное → INFO; границы классов включительно."""
    assert get_log_level_for_status(status_code) == expected_level
