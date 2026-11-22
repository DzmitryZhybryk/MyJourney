from typing import Final

from app.shared.exceptions import InternalError
from app.shared.exceptions.examples import error_response_example
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.infra.jwt import InvalidAccessTokenError, PermissionRequiredError
from app.shared.types import OpenAPIResponses

FIND_ACCOUNTS_BY_IDS_RESPONSES: Final[OpenAPIResponses] = {
    401: {
        "description": "Невалидный или истёкший access-токен",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InvalidAccessTokenError),
            }
        },
    },
    403: {
        "description": "В токене нет права на просмотр учётных записей",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(PermissionRequiredError),
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
