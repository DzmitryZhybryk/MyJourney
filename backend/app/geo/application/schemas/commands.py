from dataclasses import dataclass
from uuid import UUID

from app.geo.domain.enums import LanguageEnum

__all__ = [
    "GetCitiesByIdsCommand",
    "ResolveCitiesCommand",
    "SearchCitiesCommand",
]


@dataclass(frozen=True, slots=True)
class SearchCitiesCommand:
    """
    Намерение «найти города по префиксу имени» — вход ``CityService.search_cities``.

    Транспортный объект без валидации/семантических типов → dataclass (см. DTO
    conventions).
    """

    search_text: str
    language: LanguageEnum
    limit: int


@dataclass(frozen=True, slots=True)
class ResolveCitiesCommand:
    """Запрос названий городов по их id на нужном языке."""

    city_ids: tuple[UUID, ...]
    language: LanguageEnum


@dataclass(frozen=True, slots=True)
class GetCitiesByIdsCommand:
    """Id городов, страну и координаты которых нужно отдать."""

    city_ids: frozenset[UUID]
