"""
In-memory фейки geo: репозиторий поверх ``list[CityEntity]`` и UoW вокруг него.

Реализуют порты ``app.geo.application.ports.*`` — тот же контракт, что и боевые реализации,
поэтому ``ty`` ловит расхождение сигнатур. Репозиторий повторяет наблюдаемое поведение поиска
(префиксный матч по имени en/ru, сортировка по убыванию населения, лимит), чтобы тот же
фейк годился и на api-уровне через ``app.dependency_overrides``.
"""

from collections.abc import AsyncGenerator, Collection
from contextlib import asynccontextmanager
from uuid import UUID

from app.geo.application.ports.city_repository import CityRepositoryPort
from app.geo.application.ports.unit_of_work import GeoUnitOfWorkPort
from app.geo.domain.entities import CityEntity
from app.geo.domain.enums import LanguageEnum


class FakeCityRepository(CityRepositoryPort):
    """Фейк read-only поиска городов поверх ``list`` с префиксным матчем по имени."""

    def __init__(self) -> None:
        self.cities: list[CityEntity] = []

    async def search_cities_by_name(self, *, search_text: str, limit: int) -> tuple[CityEntity, ...]:
        prefix = search_text.strip().lower()
        matched = [
            city_entity for city_entity in self.cities if self._matches_prefix(city_entity=city_entity, prefix=prefix)
        ]
        matched.sort(key=lambda city_entity: (city_entity.population is None, -(city_entity.population or 0)))
        return tuple(matched[:limit])

    async def find_cities_by_ids(self, *, city_ids: Collection[UUID]) -> tuple[CityEntity, ...]:
        return tuple(city_entity for city_entity in self.cities if city_entity.city_id in city_ids)

    @staticmethod
    def _matches_prefix(*, city_entity: CityEntity, prefix: str) -> bool:
        """Совпадение, если имя на en ИЛИ ru начинается с префикса (как ``LIKE 'q%'`` в боевом репо)."""
        names = (
            city_entity.localized_name(language=LanguageEnum.EN),
            city_entity.localized_name(language=LanguageEnum.RU),
        )
        return any(name is not None and name.lower().startswith(prefix) for name in names)


class FakeGeoUnitOfWork(GeoUnitOfWorkPort):
    """In-memory UoW geo: фейк-репозиторий и no-op ``transaction``, считающая открытые области."""

    def __init__(self, *, city_repository: CityRepositoryPort) -> None:
        self.city_repository = city_repository
        self.transactions_started = 0

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        self.transactions_started += 1
        yield
