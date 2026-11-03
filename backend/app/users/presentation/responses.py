from typing import Final

from app.shared.exceptions import InternalError
from app.shared.exceptions.examples import error_response_example
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.infra.jwt import InvalidAccessTokenError
from app.shared.types import DictStrAny
from app.users.exceptions import UserDeletedError, UserNotFoundError

GET_CURRENT_USER_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: {
        "description": "Невалидный или истёкший access-токен",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InvalidAccessTokenError),
            }
        },
    },
    404: {
        "description": "Пользователь не найден",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(UserNotFoundError),
            }
        },
    },
    410: {
        "description": "Пользователь удалён",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(UserDeletedError),
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
