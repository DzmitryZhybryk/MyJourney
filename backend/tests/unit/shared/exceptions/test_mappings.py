import pytest

from app.media.exceptions import ObjectStoragePersistentError, ObjectStorageTemporaryError
from app.shared.exceptions.base import (
    AppError,
    ConflictError,
    GoneError,
    InternalError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    TemporaryError,
    UnauthenticatedError,
    UnprocessableError,
)
from app.shared.exceptions.mappings import resolve_http_status
from app.shared.infra.http.exceptions import ExternalAPIPersistentError, ExternalAPITemporaryError


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
        (TemporaryError(), 503),
        (InternalError(), 500),
    ],
)
def test_resolve_http_status_maps_each_category(error: AppError, expected_status: int) -> None:
    """Каждая категория резолвится в свой HTTP-статус."""
    assert resolve_http_status(error) == expected_status


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ExternalAPITemporaryError(method="POST", url="u", status=503, message="m"), 503),
        (ExternalAPIPersistentError(method="POST", url="u", status=400, message="m"), 500),
        (ObjectStorageTemporaryError(), 503),
        (ObjectStoragePersistentError(), 500),
    ],
)
def test_resolve_http_status_family_leaf_takes_category_of_second_base(error: AppError, expected_status: int) -> None:
    """Лист семьи внешнего вызова получает статус от категорийной базы, а не от маркера семьи."""
    assert resolve_http_status(error) == expected_status


def test_resolve_http_status_non_app_error_returns_500() -> None:
    """Исключение вне AppError трактуется как внутренняя ошибка (500)."""
    assert resolve_http_status(ValueError("boom")) == 500
