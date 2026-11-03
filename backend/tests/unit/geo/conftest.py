"""
Фикстуры домена geo (unit): сборка ``CityService`` на фейке UoW.

Фейки I/O-границы (``fake_city_repository``, ``fake_geo_uow``) живут в корневом
``tests/conftest.py`` — они переиспользуются и api-уровнем. Здесь остаётся только
доменно-специфичная проводка сервиса-под-тестом, чтобы тесты не повторяли её.
"""

import pytest

from app.geo.application.services.city import CityService
from tests.fakes import FakeGeoUnitOfWork


@pytest.fixture
def city_service(fake_geo_uow: FakeGeoUnitOfWork) -> CityService:
    return CityService(uow=fake_geo_uow)
