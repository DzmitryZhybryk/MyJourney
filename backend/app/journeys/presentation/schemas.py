import datetime as dt
from typing import Annotated, Self
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.journeys.domain.enums import TransportTypeEnum
from app.journeys.exceptions import InvalidYearRangeError, JourneyDateInFutureError, SameOriginAndDestinationError
from app.shared.fractional_index import MovePlacementEnum
from app.shared.pagination.schemas import CursorPageFields, CursorPaginationFields
from app.shared.schemas.base import CamelModel


class OriginAndDestination(CamelModel):
    """
    Города отправления и назначения — ``cityId`` из выдачи поиска geo.

    Отправление не может совпадать с назначением: ошибка с кодом ``journeys.same_origin_destination``,
    а не 422.
    """

    origin_city_id: UUID
    destination_city_id: UUID

    @model_validator(mode="after")
    def validate_distinct_endpoints(self) -> Self:
        """
        Отклоняет маршрут в тот же город.

        Scenarios:
            - добавление поездки
            - правка поездки в ленте «Все путешествия»
            - расстояние нового маршрута при правке поездки
        """
        if self.origin_city_id == self.destination_city_id:
            raise SameOriginAndDestinationError()

        return self


class JourneyFields(OriginAndDestination):
    """
    Поля поездки и их правила — общие для создания и правки.

    Год не может быть в будущем (по UTC) — ошибка с кодом ``journeys.date_in_future``, а не 422.
    """

    transport_type: TransportTypeEnum
    traveled_year: Annotated[int, Field(ge=1)]

    @field_validator("traveled_year")
    @classmethod
    def validate_year_not_in_future(cls, traveled_year: int) -> int:
        """
        Отклоняет год из будущего.

        Бросает доменную ошибку, а не ``ValueError``: pydantic превращает в 422 только ``ValueError``,
        ``AssertionError`` и ``PydanticCustomError``, остальные исключения доходят до общего обработчика
        со своим кодом.

        Scenarios:
            - добавление поездки
            - правка поездки в ленте «Все путешествия»
        """
        if traveled_year > dt.datetime.now(tz=dt.UTC).year:
            raise JourneyDateInFutureError()

        return traveled_year


class CreateJourneyRequest(JourneyFields):
    """Тело запроса создания поездки."""


class UpdateJourneyRequest(JourneyFields):
    """Тело запроса правки поездки: новые значения всех полей."""


class MoveJourneyRequest(CamelModel):
    """Куда перенести поездку: после или перед поездкой-соседом."""

    neighbor_journey_id: UUID
    placement: MovePlacementEnum


class MoveJourneyResponse(CamelModel):
    """Год поездки после переноса: он берётся от соседа и может смениться."""

    model_config = ConfigDict(frozen=True)

    traveled_year: int


class JourneyDistanceRequest(OriginAndDestination):
    """Города концов маршрута (query-параметры)."""


class JourneyDistanceResponse(CamelModel):
    """Расстояние маршрута по большой окружности, км — то же, что поездка сохранит."""

    model_config = ConfigDict(frozen=True)

    distance_km: int


class JourneysFeedRequest(CursorPaginationFields):
    """
    Страница ленты поездок и её фильтр (query-параметры).

    ``yearFrom`` / ``yearTo`` — включительно, один год — обе границы равны. ``transportType``
    повторяется по разу на вид транспорта; без него — все.
    """

    year_from: Annotated[int | None, Field(ge=1)] = None
    year_to: Annotated[int | None, Field(ge=1)] = None
    transport_type: frozenset[TransportTypeEnum] | None = None

    @model_validator(mode="after")
    def validate_year_range(self) -> Self:
        """
        Отклоняет диапазон лет, где начало позже конца.

        Scenarios:
            - фильтр по годам в ленте «Все путешествия»
        """
        if self.year_from is not None and self.year_to is not None and self.year_from > self.year_to:
            raise InvalidYearRangeError()

        return self


class JourneyCity(CamelModel):
    """Город поездки: его ``cityId``, страна и координаты, без названия."""

    model_config = ConfigDict(frozen=True)

    city_id: UUID
    country_code: str
    latitude: float
    longitude: float


class JourneyFeedEntry(CamelModel):
    """Поездка в ленте."""

    model_config = ConfigDict(frozen=True)

    journey_id: UUID
    origin: JourneyCity
    destination: JourneyCity
    transport_type: TransportTypeEnum
    traveled_year: int
    distance_km: int


class JourneysFeedResponse(CursorPageFields[JourneyFeedEntry]):
    """Страница ленты поездок: свежий год сверху, внутри года — порядок пользователя."""


class JourneyYearsResponse(CamelModel):
    """Годы, в которые пользователь ездил, по возрастанию, без повторов — без учёта фильтров ленты."""

    model_config = ConfigDict(frozen=True)

    years: tuple[int, ...]


class MapCity(CamelModel):
    """Город на карте путешествий: его ``cityId``, координаты и годы визитов по возрастанию."""

    model_config = ConfigDict(frozen=True)

    city_id: UUID
    latitude: float
    longitude: float
    years: tuple[int, ...]


class MapCountry(CamelModel):
    """
    Посещённая страна на карте: код ISO alpha-2 и список посещённых в ней городов.

    Имя страны не отдаём — фронт резолвит из кода через ``Intl.DisplayNames``. Статуса в
    контракте нет: эндпоинт по смыслу возвращает только посещённые страны (wishlist
    запрашивается отдельно), поэтому сам факт прихода из journeys = страна посещена.
    """

    model_config = ConfigDict(frozen=True)

    country_code: str
    cities: tuple[MapCity, ...]


class JourneysMapResponse(CamelModel):
    """
    Ответ карты путешествий: посещённые страны с городами и годами визитов.

    Каждый город встречается ровно один раз, в одной стране.
    """

    model_config = ConfigDict(frozen=True)

    countries: tuple[MapCountry, ...]


class MapPoint(CamelModel):
    """Город на глобусе или карте перемещений: его ``cityId`` и координаты, без названия."""

    model_config = ConfigDict(frozen=True)

    city_id: UUID
    latitude: float
    longitude: float


class JourneysGlobeResponse(CamelModel):
    """Ответ глобуса: города, где пользователь побывал, каждый ровно один раз."""

    model_config = ConfigDict(frozen=True)

    cities: tuple[MapPoint, ...]


class MovementsMapFilterRequest(CamelModel):
    """
    Фильтр карты перемещений (query-параметры).

    ``transportType`` повторяется по разу на вид транспорта; без него учитываются все.
    Окна лет нет: годы приходят в каждом маршруте, окно применяет фронт.
    """

    transport_type: frozenset[TransportTypeEnum] | None = None


class MovementConnection(CamelModel):
    """Стрелка на карте перемещений: откуда и куда пользователь ездил и в какие годы, по возрастанию."""

    model_config = ConfigDict(frozen=True)

    origin: MapPoint
    destination: MapPoint
    years: tuple[int, ...]


class MovementsMapResponse(CamelModel):
    """
    Ответ карты перемещений: маршруты поездок на выбранном транспорте, каждый «откуда → куда»
    один раз, с годами поездок.

    ``firstYear`` / ``lastYear`` — годы первой и последней поездки без учёта транспорта;
    ``null``, если поездок нет.
    """

    model_config = ConfigDict(frozen=True)

    first_year: int | None
    last_year: int | None
    connections: tuple[MovementConnection, ...]
