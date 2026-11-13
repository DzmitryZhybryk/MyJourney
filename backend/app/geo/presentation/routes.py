from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints

from app.geo.application.schemas.commands import ResolveCitiesCommand, SearchCitiesCommand
from app.geo.application.services.city import CityService
from app.geo.domain.enums import LanguageEnum
from app.geo.presentation.dependencies import city_service_dependency
from app.geo.presentation.responses import RESOLVE_CITIES_RESPONSES, SEARCH_CITIES_RESPONSES
from app.geo.presentation.schemas import (
    CityName,
    CitySearchItem,
    CitySearchResponse,
    ResolveCitiesRequest,
    ResolveCitiesResponse,
)
from app.shared.infra.jwt.dependency import current_user_id_dependency

geo_router = APIRouter()


@geo_router.get(
    "/cities/search/",
    response_model=CitySearchResponse,
    responses=SEARCH_CITIES_RESPONSES,
    dependencies=[Depends(current_user_id_dependency)],
)
async def search_cities(
    *,
    city_service: Annotated[CityService, Depends(city_service_dependency)],
    # Пробелы по краям срезаются до проверки длины: « M » — это поиск по одной букве, а не по трём символам.
    search_text: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=100),
        Query(alias="searchText", description="Поисковый запрос (начало имени)."),
    ],
    language: Annotated[LanguageEnum, Query(description="Язык отображаемых имён.")],
    limit: Annotated[int, Query(ge=1, le=50, description="Максимум кандидатов в выдаче.")] = 10,
) -> CitySearchResponse:
    command = SearchCitiesCommand(search_text=search_text, language=language, limit=limit)
    result = await city_service.search_cities(command=command)
    items = tuple(CitySearchItem.model_validate(item, from_attributes=True) for item in result.items)
    return CitySearchResponse(items=items)


@geo_router.post(
    "/cities/resolve/",
    response_model=ResolveCitiesResponse,
    responses=RESOLVE_CITIES_RESPONSES,
    dependencies=[Depends(current_user_id_dependency)],
)
async def resolve_cities(
    *,
    body: ResolveCitiesRequest,
    city_service: Annotated[CityService, Depends(city_service_dependency)],
) -> ResolveCitiesResponse:
    command = ResolveCitiesCommand(city_ids=tuple(body.city_ids), language=body.language)
    result = await city_service.resolve_cities(command=command)
    items = tuple(CityName.model_validate(item, from_attributes=True) for item in result.items)
    return ResolveCitiesResponse(items=items)
