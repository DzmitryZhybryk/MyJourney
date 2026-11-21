from typing import Final

from app.media.presentation.responses import INTERNAL_ERROR_RESPONSE
from app.shared.exceptions.examples import error_response_example
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.infra.jwt import InvalidAccessTokenError, PermissionRequiredError
from app.shared.types import DictStrAny
from app.shared.versioned_config import ConfigVersionConflictError

_UNAUTHENTICATED_RESPONSE: Final[DictStrAny] = {
    "description": "Невалидный или истёкший access-токен",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": error_response_example(InvalidAccessTokenError),
        }
    },
}

_PERMISSION_REQUIRED_RESPONSE: Final[DictStrAny] = {
    "description": "В токене нет права на правку конфига",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": error_response_example(PermissionRequiredError),
        }
    },
}

GET_MEDIA_CONFIG_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: _UNAUTHENTICATED_RESPONSE,
    403: _PERMISSION_REQUIRED_RESPONSE,
    500: INTERNAL_ERROR_RESPONSE,
}

UPDATE_MEDIA_CONFIG_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    401: _UNAUTHENTICATED_RESPONSE,
    403: _PERMISSION_REQUIRED_RESPONSE,
    409: {
        "description": "Правили не последнюю версию конфига — его изменили, пока правили",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(ConfigVersionConflictError),
            }
        },
    },
    500: INTERNAL_ERROR_RESPONSE,
}
