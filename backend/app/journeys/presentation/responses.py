from typing import Final

from app.journeys.exceptions import (
    InvalidMoveTargetError,
    InvalidYearRangeError,
    JourneyDateInFutureError,
    JourneyNotFoundError,
    SameOriginAndDestinationError,
    UnknownCityError,
)
from app.shared.exceptions import InternalError
from app.shared.exceptions.examples import error_response_example
from app.shared.exceptions.schemas import ErrorResponse
from app.shared.infra.jwt import InvalidAccessTokenError
from app.shared.pagination import InvalidCursorError
from app.shared.types import DictStrAny

CREATE_JOURNEY_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    400: {
        "description": "Ошибка валидации поездки",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "journeys.same_origin_destination": {
                        "summary": "Город отправления и назначения совпадают",
                        "value": error_response_example(SameOriginAndDestinationError),
                    },
                    "journeys.date_in_future": {
                        "summary": "Год поездки в будущем",
                        "value": error_response_example(JourneyDateInFutureError),
                    },
                    "journeys.unknown_city": {
                        "summary": "Города нет в справочнике",
                        "value": error_response_example(UnknownCityError),
                    },
                },
            }
        },
    },
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

JOURNEYS_FEED_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    400: {
        "description": "Ошибка запроса ленты",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "invalid_cursor": {
                        "summary": "Курсор испорчен или выдан другим списком",
                        "value": error_response_example(InvalidCursorError),
                    },
                    "journeys.invalid_year_range": {
                        "summary": "Начальный год больше конечного",
                        "value": error_response_example(InvalidYearRangeError),
                    },
                },
            }
        },
    },
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

JOURNEY_YEARS_RESPONSES: Final[dict[int | str, DictStrAny]] = {
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

JOURNEYS_MAP_RESPONSES: Final[dict[int | str, DictStrAny]] = {
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

JOURNEYS_GLOBE_RESPONSES: Final[dict[int | str, DictStrAny]] = {
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

MOVEMENTS_MAP_RESPONSES: Final[dict[int | str, DictStrAny]] = {
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

_AUTHENTICATED_RESPONSES: Final[dict[int | str, DictStrAny]] = {
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

_JOURNEY_NOT_FOUND: Final[DictStrAny] = {
    "description": "У пользователя нет такой поездки или она удалена",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": error_response_example(JourneyNotFoundError),
        }
    },
}

UPDATE_JOURNEY_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    **CREATE_JOURNEY_RESPONSES,
    404: _JOURNEY_NOT_FOUND,
}

DELETE_JOURNEY_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    **_AUTHENTICATED_RESPONSES,
    404: _JOURNEY_NOT_FOUND,
}

MOVE_JOURNEY_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    **_AUTHENTICATED_RESPONSES,
    400: {
        "description": "Соседа нет у пользователя, он удалён или это сама переносимая поездка",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": error_response_example(InvalidMoveTargetError),
            }
        },
    },
    404: _JOURNEY_NOT_FOUND,
}

JOURNEY_DISTANCE_RESPONSES: Final[dict[int | str, DictStrAny]] = {
    **_AUTHENTICATED_RESPONSES,
    400: {
        "description": "Ошибка в городах маршрута",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "examples": {
                    "journeys.same_origin_destination": {
                        "summary": "Город отправления и назначения совпадают",
                        "value": error_response_example(SameOriginAndDestinationError),
                    },
                    "journeys.unknown_city": {
                        "summary": "Города нет в справочнике",
                        "value": error_response_example(UnknownCityError),
                    },
                },
            }
        },
    },
}
