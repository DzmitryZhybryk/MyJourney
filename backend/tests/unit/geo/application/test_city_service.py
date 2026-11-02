"""Unit-тесты ``CityService`` на фейк-UoW: поиск, названия городов по id, страна и координаты городов по id."""

from uuid import uuid4

from structlog.testing import capture_logs

from app.geo.application.schemas.commands import GetCitiesByIdsCommand, ResolveCitiesCommand, SearchCitiesCommand
from app.geo.application.schemas.results import CityLocation
from app.geo.application.services.city import CityService
from app.geo.domain.enums import LanguageEnum
from tests.builders import make_city
from tests.fakes import FakeCityRepository, FakeGeoUnitOfWork


async def test_search_cities_maps_candidate_fields(
    city_service: CityService,
    fake_city_repository: FakeCityRepository,
    fake_geo_uow: FakeGeoUnitOfWork,
) -> None:
    """search_cities: поля кандидата (id, имя, страна, координаты, население) — в CitySearchItem; в транзакции.

    Сортировку по населению и обрезку по limit делает SQL-репозиторий, не сервис — они покрыты
    integration-тестом ``CityRepository`` против реального Postgres, поэтому в unit не дублируются.
    """
    moscow = make_city(en="Moscow", ru="Москва", country_code="RU", population=10_000_000)
    fake_city_repository.cities.append(moscow)

    result = await city_service.search_cities(
        SearchCitiesCommand(search_text="Mos", language=LanguageEnum.EN, limit=10),
    )

    [item] = result.items
    assert item.name == "Moscow"
    assert item.city_id == moscow.city_id
    assert item.country_code == "RU"
    assert item.latitude == moscow.latitude
    assert item.longitude == moscow.longitude
    assert item.population == moscow.population
    assert fake_geo_uow.transactions_started == 1


async def test_search_cities_resolves_names_under_language_and_flags_missing(
    city_service: CityService,
    fake_city_repository: FakeCityRepository,
) -> None:
    """search_cities: имена под язык, без перевода — фоллбэк en; такие города — одной строкой лога в порядке выдачи."""
    moscow = make_city(en="Moscow", ru="Москва", population=10_000_000)
    mosul = make_city(en="Mosul", ru=None, country_code="IQ", population=1_000_000)
    mostar = make_city(en="Mostar", ru=None, country_code="BA", population=100_000)
    fake_city_repository.cities.extend([moscow, mostar, mosul])

    with capture_logs() as logs:
        result = await city_service.search_cities(
            SearchCitiesCommand(search_text="Mos", language=LanguageEnum.RU, limit=10),
        )

    assert [item.name for item in result.items] == ["Москва", "Mosul", "Mostar"]
    missing = [log for log in logs if log["event"] == "geo.city_names_missing"]
    assert len(missing) == 1
    assert missing[0]["language"] is LanguageEnum.RU
    assert missing[0]["count"] == 2
    assert missing[0]["cities"] == (
        {"city_id": mosul.city_id, "name": "Mosul", "country_code": "IQ", "population": 1_000_000},
        {"city_id": mostar.city_id, "name": "Mostar", "country_code": "BA", "population": 100_000},
    )


async def test_resolve_cities_returns_names_in_requested_language_with_en_fallback(
    city_service: CityService,
    fake_city_repository: FakeCityRepository,
    fake_geo_uow: FakeGeoUnitOfWork,
) -> None:
    """resolve_cities: названия на языке запроса, у города без перевода — английское; чтение в транзакции."""
    moscow = make_city(en="Moscow", ru="Москва")
    mostar = make_city(en="Mostar", ru=None, country_code="BA")
    fake_city_repository.cities.extend([moscow, mostar])

    result = await city_service.resolve_cities(
        ResolveCitiesCommand(city_ids=(moscow.city_id, mostar.city_id), language=LanguageEnum.RU),
    )

    assert {item.city_id: item.name for item in result.items} == {moscow.city_id: "Москва", mostar.city_id: "Mostar"}
    assert fake_geo_uow.transactions_started == 1


async def test_resolve_cities_omits_unknown_ids_and_warns(
    city_service: CityService,
    fake_city_repository: FakeCityRepository,
) -> None:
    """resolve_cities: неизвестный id в ответ не попадает и пишется в лог предупреждением."""
    moscow = make_city()
    fake_city_repository.cities.append(moscow)
    unknown_id = uuid4()

    with capture_logs() as logs:
        result = await city_service.resolve_cities(
            ResolveCitiesCommand(city_ids=(moscow.city_id, unknown_id), language=LanguageEnum.EN),
        )

    assert [item.city_id for item in result.items] == [moscow.city_id]
    [warning] = [log for log in logs if log["event"] == "geo.city_ids_unknown"]
    assert warning["log_level"] == "warning"
    assert warning["count"] == 1
    assert warning["city_ids"] == [unknown_id]


async def test_resolve_cities_many_unknown_logs_count_and_sample(city_service: CityService) -> None:
    """resolve_cities: при множестве неизвестных id в лог идут их число и первые 10, а не весь список."""
    unknown_ids = [uuid4() for _ in range(25)]

    with capture_logs() as logs:
        await city_service.resolve_cities(ResolveCitiesCommand(city_ids=tuple(unknown_ids), language=LanguageEnum.EN))

    [warning] = [log for log in logs if log["event"] == "geo.city_ids_unknown"]
    assert warning["count"] == 25
    assert warning["city_ids"] == sorted(unknown_ids)[:10]


async def test_resolve_cities_all_known_does_not_warn(
    city_service: CityService,
    fake_city_repository: FakeCityRepository,
) -> None:
    """resolve_cities: когда все города найдены, предупреждения нет."""
    moscow = make_city()
    fake_city_repository.cities.append(moscow)

    with capture_logs() as logs:
        await city_service.resolve_cities(ResolveCitiesCommand(city_ids=(moscow.city_id,), language=LanguageEnum.EN))

    assert [log for log in logs if log["event"] == "geo.city_ids_unknown"] == []


async def test_get_cities_by_ids_returns_location_of_known_cities_only(
    city_service: CityService,
    fake_city_repository: FakeCityRepository,
    fake_geo_uow: FakeGeoUnitOfWork,
) -> None:
    """get_cities_by_ids: страна и координаты найденных городов; неизвестного id в ответе нет; чтение в транзакции."""
    moscow = make_city()
    london = make_city(en="London", ru="Лондон", country_code="GB", latitude=51.5, longitude=-0.12)
    fake_city_repository.cities.extend([moscow, london])
    unknown_id = uuid4()

    result = await city_service.get_cities_by_ids(
        command=GetCitiesByIdsCommand(city_ids=frozenset({moscow.city_id, london.city_id, unknown_id})),
    )

    assert sorted(result.items, key=lambda item: item.latitude) == [
        CityLocation(city_id=london.city_id, country_code="GB", latitude=51.5, longitude=-0.12),
        CityLocation(city_id=moscow.city_id, country_code="RU", latitude=55.75, longitude=37.62),
    ]
    assert fake_geo_uow.transactions_started == 1


async def test_get_cities_by_ids_nothing_known_returns_empty(city_service: CityService) -> None:
    """get_cities_by_ids: ни одного известного id → пустой ответ, не ошибка."""
    result = await city_service.get_cities_by_ids(command=GetCitiesByIdsCommand(city_ids=frozenset({uuid4()})))

    assert result.items == ()
