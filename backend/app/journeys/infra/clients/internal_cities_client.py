from collections.abc import Collection
from uuid import UUID

from app.geo.application.schemas.commands import GetCitiesByIdsCommand
from app.geo.application.services.city import CityService
from app.journeys.application.ports.cities_client import CitiesClientPort, CityLocationResponse


class InternalCitiesClient(CitiesClientPort):
    """Адаптер ``CitiesClientPort``: вызывает ``CityService`` из geo внутри процесса."""

    def __init__(self, city_service: CityService) -> None:
        self._city_service = city_service

    async def find_city_locations(self, *, city_ids: Collection[UUID]) -> tuple[CityLocationResponse, ...]:
        result = await self._city_service.get_cities_by_ids(
            command=GetCitiesByIdsCommand(city_ids=frozenset(city_ids)),
        )
        return tuple(
            CityLocationResponse(
                city_id=item.city_id,
                country_code=item.country_code,
                latitude=item.latitude,
                longitude=item.longitude,
            )
            for item in result.items
        )
