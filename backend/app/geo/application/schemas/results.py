from dataclasses import dataclass
from uuid import UUID

__all__ = [
    "CitiesByIdsResult",
    "CityLocation",
    "CitySearchItem",
    "CitySearchResult",
    "ResolveCitiesResult",
    "ResolvedCity",
]


@dataclass(frozen=True, slots=True)
class CitySearchItem:
    """Один вариант в подсказках поиска; имя — на языке запроса."""

    city_id: UUID
    name: str
    country_code: str
    latitude: float
    longitude: float
    population: int | None


@dataclass(frozen=True, slots=True)
class CitySearchResult:
    """Результат поиска — упорядоченная выдача кандидатов."""

    items: tuple[CitySearchItem, ...]


@dataclass(frozen=True, slots=True)
class ResolvedCity:
    """Название города на языке запроса."""

    city_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class ResolveCitiesResult:
    """Названия найденных городов."""

    items: tuple[ResolvedCity, ...]


@dataclass(frozen=True, slots=True)
class CityLocation:
    """Где находится город: страна и координаты."""

    city_id: UUID
    country_code: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class CitiesByIdsResult:
    """Найденные города в произвольном порядке; несуществующих id здесь нет."""

    items: tuple[CityLocation, ...]
