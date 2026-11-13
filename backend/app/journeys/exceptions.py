from typing import ClassVar

from app.shared.exceptions import InvalidInputError, NotFoundError
from app.shared.types import OptionalDict


class SameOriginAndDestinationError(InvalidInputError):
    code = "journeys.same_origin_destination"
    message = "Город отправления и назначения не могут совпадать"


class UnknownCityError(InvalidInputError):
    code = "journeys.unknown_city"
    message = "Город не найден"


class JourneyDateInFutureError(InvalidInputError):
    code = "journeys.date_in_future"
    message = "Год поездки не может быть в будущем"
    # Фронт показывает ошибку под полем формы с этим именем; в форме год называется `year`, не `traveledYear`.
    default_details: ClassVar[OptionalDict] = {"field": "year"}


class InvalidYearRangeError(InvalidInputError):
    code = "journeys.invalid_year_range"
    message = "Начальный год не может быть больше конечного"


class JourneyNotFoundError(NotFoundError):
    code = "journeys.journey_not_found"
    message = "Поездка не найдена"


class InvalidMoveTargetError(InvalidInputError):
    code = "journeys.invalid_move_target"
    message = "Некорректная поездка-сосед для переноса"
