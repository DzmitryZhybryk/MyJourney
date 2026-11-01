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

__all__ = [
    # Базовые исключения
    "AppError",
    "ConflictError",
    # Категории
    "ErrorCategoryEnum",
    "GoneError",
    "InternalError",
    "InvalidInputError",
    "InvariantViolationError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitedError",
    "UnauthenticatedError",
    "UnprocessableError",
]
