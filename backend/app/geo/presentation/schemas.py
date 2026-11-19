from typing import Annotated
from uuid import UUID

from pydantic import ConfigDict, Field

from app.geo.domain.enums import LanguageEnum
from app.shared.schemas.base import CamelModel


class CitySearchItem(CamelModel):
    """Один вариант в подсказках поиска; по ``cityId`` на город потом можно ссылаться."""

    model_config = ConfigDict(frozen=True)

    city_id: UUID
    name: Annotated[str, Field(description="Имя города, резолвнутое под язык запроса (параметр language).")]
    country_code: str
    latitude: float
    longitude: float
    population: int | None


class CitySearchResponse(CamelModel):
    """Ответ автокомплита — упорядоченная выдача кандидатов (по убыванию населения)."""

    model_config = ConfigDict(frozen=True)

    items: tuple[CitySearchItem, ...]


class ResolveCitiesRequest(CamelModel):
    """Запрос названий городов по их id на нужном языке."""

    city_ids: Annotated[list[UUID], Field(min_length=1, max_length=1000)]
    language: LanguageEnum


class CityName(CamelModel):
    """Название города на языке запроса."""

    model_config = ConfigDict(frozen=True)

    city_id: UUID
    name: str


class ResolveCitiesResponse(CamelModel):
    """Названия найденных городов; id, которых нет в газеттире, в ответ не попадают."""

    model_config = ConfigDict(frozen=True)

    items: tuple[CityName, ...]
