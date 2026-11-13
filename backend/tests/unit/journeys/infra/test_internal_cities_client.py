"""
Юнит-тест адаптера ``InternalCitiesClient`` (journeys → geo).

Реальный ``CityService`` на фейковом репозитории geo; фейкаем только I/O-границу geo. Api-тесты
journeys подменяют клиента целиком, поэтому стык «journeys спрашивает — geo отвечает» проверяется
только здесь.
"""

from uuid import uuid4

from app.geo.application.services.city import CityService
from app.journeys.application.ports.cities_client import CityLocationResponse
from app.journeys.infra.clients.internal_cities_client import InternalCitiesClient
from tests.builders import make_city
from tests.fakes import FakeCityRepository, FakeGeoUnitOfWork


async def test_find_city_locations_maps_known_cities_from_geo() -> None:
    """find_city_locations: страна и координаты городов из справочника geo, неизвестного id в ответе нет."""
    moscow = make_city()
    london = make_city(en="London", ru="Лондон", country_code="GB", latitude=51.5, longitude=-0.12)
    city_repository = FakeCityRepository()
    city_repository.cities.extend([moscow, london])
    client = InternalCitiesClient(
        city_service=CityService(uow=FakeGeoUnitOfWork(city_repository=city_repository)),
    )

    locations = await client.find_city_locations(city_ids=(moscow.city_id, london.city_id, uuid4()))

    assert sorted(locations, key=lambda location: location.latitude) == [
        CityLocationResponse(city_id=london.city_id, country_code="GB", latitude=51.5, longitude=-0.12),
        CityLocationResponse(city_id=moscow.city_id, country_code="RU", latitude=55.75, longitude=37.62),
    ]
