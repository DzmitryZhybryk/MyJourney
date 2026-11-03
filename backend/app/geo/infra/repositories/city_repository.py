from collections.abc import Collection
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.application.ports.city_repository import CityRepositoryPort
from app.geo.domain.entities import CityEntity
from app.geo.domain.value_objects import LocalizedNames
from app.geo.infra.models import GeoCity
from app.shared.repositories.base_repository import BaseDBRepository

# Бэкслеш как ESCAPE в LIKE: метасимволы пользовательского ввода (% _ \) экранируем,
# чтобы они не работали как шаблон (юзер ищет литералы, а не wildcard'ы).
_LIKE_ESCAPE = "\\"


class CityRepository(BaseDBRepository[GeoCity], CityRepositoryPort):
    """Чтение городов из газеттира: поиск по началу имени и выборка по id."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=GeoCity)

    async def search_cities_by_name(self, *, search_text: str, limit: int) -> tuple[CityEntity, ...]:
        query = self._prefix_query(search_text=search_text)
        # По убыванию населения (без населения — в конце), tie-break по external_id.
        query = query.order_by(GeoCity.population.desc().nulls_last(), GeoCity.external_id).limit(limit)
        result = await self._session.execute(query)
        return tuple(self._to_entity(city_model=city_model) for city_model in result.scalars())

    async def find_cities_by_ids(self, *, city_ids: Collection[UUID]) -> tuple[CityEntity, ...]:
        query = select(GeoCity).where(GeoCity.id.in_(city_ids))
        result = await self._session.execute(query)
        return tuple(self._to_entity(city_model=city_model) for city_model in result.scalars())

    def _prefix_query(self, *, search_text: str) -> Select[GeoCity]:
        """
        Префиксный матч ``lower(name) LIKE 'q%'`` по ``name_en``/``name_ru``.

        Ложится на btree ``text_pattern_ops`` по ``lower(name_*)`` — берётся
        range-scan'ом для запроса любой длины (даже 1 символ).

        Scenarios:
            - автокомплит города в полях маршрута
        """
        prefix = f"{self._escape_like(search_text).lower()}%"
        return select(GeoCity).where(
            or_(
                func.lower(GeoCity.name_en).like(prefix, escape=_LIKE_ESCAPE),
                func.lower(GeoCity.name_ru).like(prefix, escape=_LIKE_ESCAPE),
            ),
        )

    @staticmethod
    def _escape_like(search_text: str) -> str:
        """
        Экранирует LIKE-метасимволы (``\\`` ``%`` ``_``) в пользовательском вводе.

        Scenarios:
            - автокомплит города в полях маршрута
        """
        return (
            search_text.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
            .replace("%", f"{_LIKE_ESCAPE}%")
            .replace("_", f"{_LIKE_ESCAPE}_")
        )

    @staticmethod
    def _to_entity(*, city_model: GeoCity) -> CityEntity:
        return CityEntity(
            city_id=city_model.id,
            names=LocalizedNames(en=city_model.name_en, ru=city_model.name_ru),
            country_code=city_model.country_code,
            latitude=city_model.latitude,
            longitude=city_model.longitude,
            population=city_model.population,
        )
