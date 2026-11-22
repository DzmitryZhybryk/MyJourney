from typing import Final

from app.shared.exceptions import InternalError
from app.shared.exceptions.examples import error_response_example
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.types import DictStrAny, OpenAPIResponses

INTERNAL_ERROR_RESPONSE: Final[DictStrAny] = {
    "description": "Внутренняя ошибка сервера",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": error_response_example(InternalError),
        }
    },
}

GET_UPLOAD_RULES_RESPONSES: Final[OpenAPIResponses] = {
    500: INTERNAL_ERROR_RESPONSE,
}
