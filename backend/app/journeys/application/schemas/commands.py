from dataclasses import dataclass
from uuid import UUID

from app.journeys.application.ports.journey_repository import JourneyFilters
from app.journeys.domain.enums import TransportTypeEnum
from app.shared.fractional_index import MovePlacementEnum
from app.shared.pagination import PageQuery

__all__ = [
    "CreateJourneyCommand",
    "EstimateJourneyDistanceCommand",
    "GetMovementsMapCommand",
    "ListJourneysCommand",
    "MoveJourneyCommand",
    "UpdateJourneyCommand",
]


@dataclass(frozen=True, slots=True)
class CreateJourneyCommand:
    """Данные для создания поездки."""

    origin_city_id: UUID
    destination_city_id: UUID
    transport_type: TransportTypeEnum
    traveled_year: int


@dataclass(frozen=True, slots=True)
class UpdateJourneyCommand:
    """Новые значения всех полей поездки: правка заменяет поездку целиком."""

    origin_city_id: UUID
    destination_city_id: UUID
    transport_type: TransportTypeEnum
    traveled_year: int


@dataclass(frozen=True, slots=True)
class MoveJourneyCommand:
    """Куда перенести поездку: после или перед поездкой-соседом."""

    neighbor_journey_id: UUID
    placement: MovePlacementEnum


@dataclass(frozen=True, slots=True)
class EstimateJourneyDistanceCommand:
    """Города концов маршрута, расстояние между которыми нужно посчитать."""

    origin_city_id: UUID
    destination_city_id: UUID


@dataclass(frozen=True, slots=True)
class ListJourneysCommand:
    """Какую страницу ленты поездок отдать и с каким фильтром."""

    page: PageQuery
    filters: JourneyFilters


@dataclass(frozen=True, slots=True)
class GetMovementsMapCommand:
    """
    Фильтр карты перемещений.

    ``transport_types`` — виды транспорта, поездки на которых учитываются; ``None`` — все.
    Окна лет здесь нет: годы маршрутов уходят на фронт, и окно он применяет сам.
    """

    transport_types: frozenset[TransportTypeEnum] | None
