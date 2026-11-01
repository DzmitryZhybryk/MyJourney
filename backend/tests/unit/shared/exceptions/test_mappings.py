import pytest

from app.shared.exceptions.base import (
    AppError,
    ConflictError,
    GoneError,
    InternalError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    UnauthenticatedError,
    UnprocessableError,
)
from app.shared.exceptions.mappings import resolve_http_status


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (InvalidInputError(), 400),
        (UnauthenticatedError(), 401),
        (PermissionDeniedError(), 403),
        (NotFoundError(), 404),
        (ConflictError(), 409),
        (GoneError(), 410),
        (UnprocessableError(), 422),
        (RateLimitedError(), 429),
        (InternalError(), 500),
    ],
)
def test_resolve_http_status_maps_each_category(error: AppError, expected_status: int) -> None:
    """Каждая категория резолвится в свой HTTP-статус."""
    assert resolve_http_status(error) == expected_status


def test_resolve_http_status_non_app_error_returns_500() -> None:
    """Исключение вне AppError трактуется как внутренняя ошибка (500)."""
    assert resolve_http_status(ValueError("boom")) == 500
