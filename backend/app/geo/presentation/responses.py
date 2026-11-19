from typing import Final

from app.shared.exceptions import InternalError
from app.shared.exceptions.examples import error_response_example
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.infra.jwt import InvalidAccessTokenError
from app.shared.types import DictStrAny

SEARCH_CITIES_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: {
        "description": "Невалидный или истёкший access-токен",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InvalidAccessTokenError),
            }
        },
    },
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}

RESOLVE_CITIES_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: {
        "description": "Невалидный или истёкший access-токен",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InvalidAccessTokenError),
            }
        },
    },
    500: {
        "description": "Внутренняя ошибка сервера",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InternalError),
            }
        },
    },
}
