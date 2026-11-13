from dataclasses import dataclass
from uuid import UUID

from app.journeys.application.ports.journey_repository import MovementConnection
from app.journeys.domain.enums import TransportTypeEnum
from app.journeys.domain.value_objects import GeoPoint
from app.shared.pagination import CursorPage

__all__ = [
    "JourneyDistanceResult",
    "JourneyFeedItem",
    "JourneyYearsResult",
    "JourneysGlobeResult",
    "JourneysMapResult",
    "ListJourneysResult",
    "MapCityVisit",
    "MapCountryVisits",
    "MoveJourneyResult",
    "MovementsMapResult",
]


@dataclass(frozen=True, slots=True)
class MoveJourneyResult:
    """Год поездки после переноса: он берётся от соседа и может смениться."""

    traveled_year: int


@dataclass(frozen=True, slots=True)
class JourneyDistanceResult:
    """Расстояние маршрута по большой окружности, км — то же, что поездка сохранит."""

    distance_km: int


@dataclass(frozen=True, slots=True)
class MapCityVisit:
    """
    Посещённый город на карте путешествий.

    ``years`` — годы поездок, в которых город был отправлением или назначением, по возрастанию.
    Названия нет: фронт запрашивает его у geo по ``city_id``.
    """

    city_id: UUID
    latitude: float
    longitude: float
    years: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MapCountryVisits:
    """
    Посещённая страна (ISO alpha-2) и города, посещённые в ней пользователем.

    Имя страны не несём: фронт резолвит его из кода через ``Intl.DisplayNames`` (см.
    country-code-contract). ``cities`` непустой — страна попадает в агрегат только если в ней
    есть хотя бы один посещённый город.
    """

    country_code: str
    cities: tuple[MapCityVisit, ...]


@dataclass(frozen=True, slots=True)
class JourneysMapResult:
    """Агрегат карты путешествий: посещённые страны с городами и годами визитов."""

    countries: tuple[MapCountryVisits, ...]


@dataclass(frozen=True, slots=True)
class JourneysGlobeResult:
    """Посещённые города для глобуса, каждый по одному разу."""

    cities: tuple[GeoPoint, ...]


@dataclass(frozen=True, slots=True)
class MovementsMapResult:
    """
    Карта перемещений: маршруты поездок на выбранном транспорте, с годами поездок.

    ``first_year`` и ``last_year`` — годы первой и последней поездки пользователя без учёта
    транспорта, ``None`` — поездок нет.
    """

    first_year: int | None
    last_year: int | None
    connections: tuple[MovementConnection, ...]


@dataclass(frozen=True, slots=True)
class JourneyFeedItem:
    """Поездка в ленте. Названий городов нет: фронт запрашивает их у geo по ``city_id``."""

    journey_id: UUID
    origin: GeoPoint
    destination: GeoPoint
    transport_type: TransportTypeEnum
    traveled_year: int
    distance_km: int


@dataclass(frozen=True, slots=True)
class ListJourneysResult(CursorPage[JourneyFeedItem]):
    """
    Страница ленты поездок.

    Порядок — свежий год сверху, внутри года — порядок, заданный пользователем.
    """


@dataclass(frozen=True, slots=True)
class JourneyYearsResult:
    """Годы, в которые пользователь ездил, по возрастанию — без учёта фильтров ленты."""

    years: tuple[int, ...]
