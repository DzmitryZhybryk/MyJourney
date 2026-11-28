"""
Фикстуры unit-уровня, нужные больше чем одному домену.

``jwt_service`` собран с литеральным секретом в обход ``settings``; api-уровень его переиспользовать не
может — приложение декодирует токен секретом из ``settings``.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from app.geo.application.services.city import CityService
from app.shared.infra.jwt.service import JWTService
from app.users.application.services.user import UserService
from tests.fakes import FakeEventPublisher, FakeGeoUnitOfWork, FakeUserUnitOfWork

# tests/unit/<этот файл> → backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_JWT_SECRET = "unit-test-secret-at-least-32-bytes-long"
_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 15


@pytest.fixture
def jwt_secret() -> str:
    return _JWT_SECRET


@pytest.fixture
def jwt_algorithm() -> str:
    return _JWT_ALGORITHM


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(
        secret=_JWT_SECRET,
        algorithm=_JWT_ALGORITHM,
        access_token_expire_minutes=_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@pytest.fixture
def user_service(fake_user_uow: FakeUserUnitOfWork, fake_event_publisher: FakeEventPublisher) -> UserService:
    return UserService(uow=fake_user_uow, event_publisher=fake_event_publisher)


@pytest.fixture
def city_service(fake_geo_uow: FakeGeoUnitOfWork) -> CityService:
    return CityService(uow=fake_geo_uow)


@pytest.fixture(scope="session")
def module_name_of() -> Callable[[Path], str]:
    """
    Имя модуля по пути его файла в ``backend/``: ``app/geo/domain/city.py`` → ``app.geo.domain.city``,
    ``app/geo/__init__.py`` → ``app.geo``.
    """

    def _module_name(path: Path) -> str:
        parts = path.resolve().relative_to(_BACKEND_DIR).with_suffix("").parts
        return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)

    return _module_name
