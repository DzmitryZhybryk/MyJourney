"""Api-тесты journeys подменяют клиента городов целиком, поэтому стык journeys и geo проверяется только здесь."""

from uuid import uuid4

from app.geo.application.services.city import CityService
from app.journeys.application.ports.cities_client import CityLocationResponse
from app.journeys.infra.clients.internal_cities_client import InternalCitiesClient
from tests.builders import make_city
from tests.fakes import FakeCityRepository


async def test_find_city_locations_maps_known_cities_from_geo(
    city_service: CityService,
    fake_city_repository: FakeCityRepository,
) -> None:
    """Страна и координаты городов берутся из справочника geo; неизвестного id в ответе нет."""
    moscow = make_city()
    london = make_city(en="London", ru="Лондон", country_code="GB", latitude=51.5, longitude=-0.12)
    fake_city_repository.cities.extend([moscow, london])

    locations = await InternalCitiesClient(city_service).find_city_locations((moscow.city_id, london.city_id, uuid4()))

    assert locations == frozenset(
        {
            CityLocationResponse(city_id=london.city_id, country_code="GB", latitude=51.5, longitude=-0.12),
            CityLocationResponse(city_id=moscow.city_id, country_code="RU", latitude=55.75, longitude=37.62),
        }
    )
