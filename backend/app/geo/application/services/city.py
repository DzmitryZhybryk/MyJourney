from app.geo.application.ports.unit_of_work import GeoUnitOfWorkPort
from app.geo.application.schemas.commands import GetCitiesByIdsCommand, ResolveCitiesCommand, SearchCitiesCommand
from app.geo.application.schemas.results import (
    CitiesByIdsResult,
    CityLocation,
    CitySearchItem,
    CitySearchResult,
    ResolveCitiesResult,
    ResolvedCity,
)
from app.shared.logging import get_logger
from app.shared.types import DictStrAny

logger = get_logger(__name__)


class CityService:
    """Поиск городов в газеттире и их названия на нужном языке."""

    def __init__(self, *, uow: GeoUnitOfWorkPort, logged_unknown_city_ids_limit: int = 10) -> None:
        """
        Args:
            uow: Транзакция и репозиторий городов
            logged_unknown_city_ids_limit: Сколько неизвестных id попадает в лог — для сигнала хватает
                примера, а весь запрос — до 1000 id
        """
        self._uow = uow
        self._logged_unknown_city_ids_limit = logged_unknown_city_ids_limit

    async def search_cities(self, command: SearchCitiesCommand) -> CitySearchResult:
        """
        Ищет города под автокомплит по префиксу имени и резолвит их имена под язык запроса.

        Scenarios:
            - автокомплит города в полях маршрута «Откуда» и «Куда»

        Args:
            command: Запрос автокомплита (текст, язык, лимит)

        Returns:
            Упорядоченная выдача кандидатов с именами под язык запроса
        """
        async with self._uow.transaction():
            cities = await self._uow.city_repository.search_cities_by_name(
                search_text=command.search_text,
                limit=command.limit,
            )

        items: list[CitySearchItem] = []
        cities_without_name: list[DictStrAny] = []
        for city_entity in cities:
            name = city_entity.display_name(language=command.language)
            if city_entity.localized_name(language=command.language) is None:
                cities_without_name.append(
                    {
                        "city_id": city_entity.city_id,
                        "name": name,
                        "country_code": city_entity.country_code,
                        "population": city_entity.population,
                    }
                )

            items.append(
                CitySearchItem(
                    city_id=city_entity.city_id,
                    name=name,
                    country_code=city_entity.country_code,
                    latitude=city_entity.latitude,
                    longitude=city_entity.longitude,
                    population=city_entity.population,
                )
            )

        if cities_without_name:
            logger.info(
                "geo.city_names_missing",
                language=command.language,
                count=len(cities_without_name),
                cities=tuple(cities_without_name),
            )

        return CitySearchResult(items=tuple(items))

    async def resolve_cities(self, command: ResolveCitiesCommand) -> ResolveCitiesResult:
        """
        Возвращает названия городов по их id на языке запроса; если перевода на этот язык нет,
        отдаётся английское название.

        Id, которых нет в газеттире, в ответ не попадают и пишутся в лог предупреждением:
        газеттир города не удаляет, так что неизвестный id — это сбой, а не норма.

        Scenarios:
            - названия городов на картах, глобусе и в ленте на языке интерфейса

        Args:
            command: Id городов и язык

        Returns:
            Названия найденных городов
        """
        async with self._uow.transaction():
            cities = await self._uow.city_repository.find_cities_by_ids(city_ids=command.city_ids)

        missing_city_ids = set(command.city_ids) - {city_entity.city_id for city_entity in cities}
        if missing_city_ids:
            logger.warning(
                "geo.city_ids_unknown",
                count=len(missing_city_ids),
                city_ids=sorted(missing_city_ids)[: self._logged_unknown_city_ids_limit],
            )

        items = tuple(
            ResolvedCity(city_id=city_entity.city_id, name=city_entity.display_name(language=command.language))
            for city_entity in cities
        )
        return ResolveCitiesResult(items=items)

    async def get_cities_by_ids(self, command: GetCitiesByIdsCommand) -> CitiesByIdsResult:
        """
        Отдаёт страну и координаты городов по их id.

        Страна и координаты берутся из газеттира, а не со слов клиента. Id, которых нет в
        газеттире, в ответ не попадают — их отсутствие и есть ответ «такого города нет».

        Scenarios:
            - домен, который принимает id городов извне и хранит у себя их страну и координаты

        Args:
            command: Id городов

        Returns:
            Найденные города в произвольном порядке
        """
        async with self._uow.transaction():
            cities = await self._uow.city_repository.find_cities_by_ids(city_ids=command.city_ids)

        items = tuple(
            CityLocation(
                city_id=city_entity.city_id,
                country_code=city_entity.country_code,
                latitude=city_entity.latitude,
                longitude=city_entity.longitude,
            )
            for city_entity in cities
        )
        return CitiesByIdsResult(items=items)
