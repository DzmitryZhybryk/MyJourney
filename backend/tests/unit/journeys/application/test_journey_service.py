import datetime as dt
from uuid import UUID, uuid4

import pytest

from app.journeys.application.ports.journey_repository import JourneyFilters, MovementConnection, VisitedCity
from app.journeys.application.schemas.commands import (
    CreateJourneyCommand,
    EstimateJourneyDistanceCommand,
    GetMovementsMapCommand,
    ListJourneysCommand,
    MoveJourneyCommand,
    UpdateJourneyCommand,
)
from app.journeys.application.schemas.results import (
    JourneyFeedItem,
    JourneysMapResult,
    JourneyYearsResult,
    MapCityVisit,
    MapCountryVisits,
    MoveJourneyResult,
    MovementsMapResult,
)
from app.journeys.application.services.journey import JourneyService
from app.journeys.domain.enums import TransportTypeEnum
from app.journeys.exceptions import (
    InvalidMoveTargetError,
    JourneyNotFoundError,
    UnknownCityError,
)
from app.shared.fractional_index import MovePlacementEnum
from app.shared.pagination.cursor import CursorPageQuery
from tests.builders import LONDON_CITY_ID, LONDON_POINT, MOSCOW_CITY_ID, MOSCOW_POINT, make_geo_point, make_journey
from tests.fakes import FakeCitiesClient, FakeJourneyRepository, FakeJourneyUnitOfWork, MovementConnectionQuery

_DELETED_AT = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


async def test_create_journey_snapshots_cities_and_commits(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    fake_cities_client: FakeCitiesClient,
) -> None:
    """Страна и координаты городов — из geo; поездка вставлена со своим годом, один коммит."""
    user_id = uuid4()
    command = CreateJourneyCommand(
        origin_city_id=MOSCOW_CITY_ID,
        destination_city_id=LONDON_CITY_ID,
        transport_type=TransportTypeEnum.AIR,
        traveled_year=2020,
    )

    await journey_service.create_journey(user_id=user_id, command=command)

    assert len(fake_journey_repository.journeys) == 1
    journey = fake_journey_repository.journeys[0]
    assert journey.user_id == user_id
    assert journey.origin.city_id == MOSCOW_CITY_ID
    assert journey.origin.country_code == "RU"
    assert journey.destination.city_id == LONDON_CITY_ID
    assert journey.destination.latitude == pytest.approx(51.5)
    assert journey.transport_type is TransportTypeEnum.AIR
    assert journey.traveled_year == 2020
    assert journey.distance_km == pytest.approx(2500, abs=60)
    fake_journey_uow.commit_mock.assert_awaited_once()
    assert fake_journey_uow.transactions_started == 1
    assert fake_cities_client.calls == [(MOSCOW_CITY_ID, LONDON_CITY_ID)]


@pytest.mark.parametrize("missing_ids", [(MOSCOW_CITY_ID,), (LONDON_CITY_ID,), (MOSCOW_CITY_ID, LONDON_CITY_ID)])
async def test_create_journey_unknown_cities_rejected_before_transaction(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    fake_cities_client: FakeCitiesClient,
    missing_ids: tuple[UUID, ...],
) -> None:
    """Неизвестные origin, destination или оба дают точные id ошибки без транзакции и вставки."""
    for city_id in missing_ids:
        del fake_cities_client.locations[city_id]
    command = CreateJourneyCommand(
        origin_city_id=MOSCOW_CITY_ID,
        destination_city_id=LONDON_CITY_ID,
        transport_type=TransportTypeEnum.AIR,
        traveled_year=2020,
    )

    with pytest.raises(UnknownCityError) as exc_info:
        await journey_service.create_journey(user_id=uuid4(), command=command)

    assert exc_info.value.details == {"city_ids": frozenset(missing_ids)}
    assert fake_journey_repository.journeys == []
    assert fake_journey_uow.transactions_started == 0
    fake_journey_uow.commit_mock.assert_not_awaited()
    assert fake_cities_client.calls == [(MOSCOW_CITY_ID, LONDON_CITY_ID)]


async def test_create_journey_matches_geo_cities_by_id_not_by_order(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
    fake_cities_client: FakeCitiesClient,
) -> None:
    """geo отдаёт города в обратном порядке — отправление всё равно Москва, назначение Лондон."""
    fake_cities_client.locations = dict(reversed(fake_cities_client.locations.items()))
    command = CreateJourneyCommand(
        origin_city_id=MOSCOW_CITY_ID,
        destination_city_id=LONDON_CITY_ID,
        transport_type=TransportTypeEnum.AIR,
        traveled_year=2020,
    )

    await journey_service.create_journey(user_id=uuid4(), command=command)

    journey = fake_journey_repository.journeys[0]
    assert (journey.origin.city_id, journey.origin.country_code) == (MOSCOW_CITY_ID, "RU")
    assert journey.origin.latitude == pytest.approx(55.75)
    assert (journey.destination.city_id, journey.destination.country_code) == (LONDON_CITY_ID, "GB")
    assert journey.destination.latitude == pytest.approx(51.5)


async def test_get_journeys_map_no_journeys_returns_empty(journey_service: JourneyService) -> None:
    """Поездок нет → пустой агрегат без стран."""
    result = await journey_service.get_journeys_map(uuid4())

    assert result == JourneysMapResult(())


async def test_get_journeys_map_groups_cities_by_country(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
    fake_journey_uow: FakeJourneyUnitOfWork,
) -> None:
    """Города подряд по стране собираются в страны с городами и годами; чтение в транзакции."""
    user_id = uuid4()
    paris_id = uuid4()
    fake_journey_repository.visited_cities_by_user_id[user_id] = [
        VisitedCity(
            city=make_geo_point(city_id=paris_id, country_code="FR", latitude=48.85, longitude=2.35), years=(2021,)
        ),
        VisitedCity(city=LONDON_POINT, years=(2019, 2021)),
        VisitedCity(city=MOSCOW_POINT, years=(2019,)),
    ]

    result = await journey_service.get_journeys_map(user_id)

    assert result == JourneysMapResult(
        (
            MapCountryVisits(
                country_code="FR",
                cities=(MapCityVisit(city_id=paris_id, latitude=48.85, longitude=2.35, years=(2021,)),),
            ),
            MapCountryVisits(
                country_code="GB",
                cities=(MapCityVisit(city_id=LONDON_CITY_ID, latitude=51.5, longitude=-0.12, years=(2019, 2021)),),
            ),
            MapCountryVisits(
                country_code="RU",
                cities=(MapCityVisit(city_id=MOSCOW_CITY_ID, latitude=55.75, longitude=37.62, years=(2019,)),),
            ),
        )
    )
    assert fake_journey_uow.transactions_started == 1


async def test_get_journeys_map_keeps_several_cities_of_one_country_together(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
) -> None:
    """Два города одной страны — одна страна с двумя городами в порядке репозитория."""
    user_id = uuid4()
    petersburg_id = uuid4()
    petersburg = make_geo_point(city_id=petersburg_id, country_code="RU", latitude=59.94, longitude=30.31)
    fake_journey_repository.visited_cities_by_user_id[user_id] = [
        VisitedCity(city=MOSCOW_POINT, years=(2020,)),
        VisitedCity(city=petersburg, years=(2021,)),
    ]

    result = await journey_service.get_journeys_map(user_id)

    assert [country.country_code for country in result.countries] == ["RU"]
    assert [city.city_id for city in result.countries[0].cities] == [MOSCOW_CITY_ID, petersburg_id]


async def test_get_journeys_globe_returns_cities_without_years(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
    fake_journey_uow: FakeJourneyUnitOfWork,
) -> None:
    """Те же города, что у карты, каждый по одному разу; чтение в транзакции."""
    user_id = uuid4()
    fake_journey_repository.visited_cities_by_user_id[user_id] = [
        VisitedCity(city=LONDON_POINT, years=(2019, 2021)),
        VisitedCity(city=MOSCOW_POINT, years=(2019,)),
    ]

    result = await journey_service.get_journeys_globe(user_id)

    assert [city.city_id for city in result.cities] == [LONDON_CITY_ID, MOSCOW_CITY_ID]
    assert result.cities[1].latitude == pytest.approx(55.75)
    assert fake_journey_uow.transactions_started == 1


async def test_get_movements_map_returns_connections_and_year_bounds(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
    fake_journey_uow: FakeJourneyUnitOfWork,
) -> None:
    """Маршруты с годами и годы первой и последней поездки; транспорт доходит до запроса."""
    user_id = uuid4()
    connection = MovementConnection(origin=MOSCOW_POINT, destination=LONDON_POINT, years=(2019, 2021))
    fake_journey_repository.journeys = [
        make_journey(user_id=user_id, traveled_year=2019),
        make_journey(user_id=user_id, traveled_year=2022),
        make_journey(user_id=user_id, traveled_year=2017),
    ]
    fake_journey_repository.movement_connections_by_user_id[user_id] = [connection]
    command = GetMovementsMapCommand(frozenset({TransportTypeEnum.AIR}))

    result = await journey_service.get_movements_map(user_id=user_id, command=command)

    assert result == MovementsMapResult(first_year=2017, last_year=2022, connections=(connection,))
    assert fake_journey_repository.movement_connection_queries == [
        MovementConnectionQuery(user_id=user_id, transport_types=frozenset({TransportTypeEnum.AIR}))
    ]
    assert fake_journey_uow.transactions_started == 1


async def test_get_movements_map_without_journeys_skips_connections_query(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
    fake_journey_uow: FakeJourneyUnitOfWork,
) -> None:
    """Поездок нет → пустой ответ без годов, маршруты не запрашиваются; чтение в транзакции."""
    user_id = uuid4()
    command = GetMovementsMapCommand(None)

    result = await journey_service.get_movements_map(user_id=user_id, command=command)

    assert result == MovementsMapResult(first_year=None, last_year=None, connections=())
    assert fake_journey_repository.movement_connection_queries == []
    assert fake_journey_uow.transactions_started == 1


async def test_create_journey_goes_to_end_of_its_year(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
) -> None:
    """Новая поездка встаёт после неудалённых поездок своего года; другие годы и удалённые не мешают."""
    user_id = uuid4()
    fake_journey_repository.journeys = [
        make_journey(user_id=user_id, traveled_year=2020, sort_key="m"),
        make_journey(user_id=user_id, traveled_year=2020, sort_key="z", deleted_at=_DELETED_AT),
        make_journey(user_id=user_id, traveled_year=2021, sort_key="y"),
    ]
    command = CreateJourneyCommand(
        origin_city_id=MOSCOW_CITY_ID,
        destination_city_id=LONDON_CITY_ID,
        transport_type=TransportTypeEnum.AIR,
        traveled_year=2020,
    )

    await journey_service.create_journey(user_id=user_id, command=command)

    created = fake_journey_repository.journeys[-1]
    assert "m" < created.sort_key < "z"


async def test_update_journey_same_year_replaces_fields_and_keeps_position(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
) -> None:
    """Тот же год: города, транспорт и пересчитанное расстояние новые, ключ прежний."""
    user_id = uuid4()
    journey_entity = make_journey(
        user_id=user_id,
        origin=LONDON_POINT,
        destination=MOSCOW_POINT,
        transport_type=TransportTypeEnum.WATER,
        distance_km=1,
        traveled_year=2020,
        sort_key="m",
    )
    fake_journey_repository.journeys = [journey_entity]

    await journey_service.update_journey(
        user_id=user_id,
        journey_id=journey_entity.journey_id,
        command=UpdateJourneyCommand(
            origin_city_id=MOSCOW_CITY_ID,
            destination_city_id=LONDON_CITY_ID,
            transport_type=TransportTypeEnum.AIR,
            traveled_year=2020,
        ),
    )

    updated = fake_journey_repository.journeys[0]
    assert updated.origin.city_id == MOSCOW_CITY_ID
    assert updated.destination.city_id == LONDON_CITY_ID
    assert updated.transport_type is TransportTypeEnum.AIR
    assert updated.distance_km == pytest.approx(2500, abs=60)
    assert updated.traveled_year == 2020
    assert updated.sort_key == "m"
    fake_journey_uow.commit_mock.assert_awaited_once()


async def test_update_journey_new_year_goes_to_end_of_that_year(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
) -> None:
    """Смена года: поездка встаёт в конец нового года."""
    user_id = uuid4()
    journey_entity = make_journey(user_id=user_id, traveled_year=2020, sort_key="m")
    fake_journey_repository.journeys = [
        journey_entity,
        make_journey(user_id=user_id, traveled_year=2018, sort_key="t"),
    ]

    await journey_service.update_journey(
        user_id=user_id,
        journey_id=journey_entity.journey_id,
        command=UpdateJourneyCommand(
            origin_city_id=MOSCOW_CITY_ID,
            destination_city_id=LONDON_CITY_ID,
            transport_type=TransportTypeEnum.AIR,
            traveled_year=2018,
        ),
    )

    updated = fake_journey_repository.journeys[0]
    assert updated.traveled_year == 2018
    assert updated.sort_key > "t"


@pytest.mark.parametrize("case", ["missing", "foreign", "deleted"])
async def test_update_journey_unavailable_journey_raises_not_found(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    case: str,
) -> None:
    """Несуществующая, чужая или удалённая поездка → ``JourneyNotFoundError`` без коммита."""
    user_id = uuid4()
    journey_entity = make_journey(
        user_id=uuid4() if case == "foreign" else user_id,
        deleted_at=_DELETED_AT if case == "deleted" else None,
    )
    if case != "missing":
        fake_journey_repository.journeys = [journey_entity]

    with pytest.raises(JourneyNotFoundError):
        await journey_service.update_journey(
            user_id=user_id,
            journey_id=journey_entity.journey_id,
            command=UpdateJourneyCommand(
                origin_city_id=MOSCOW_CITY_ID,
                destination_city_id=LONDON_CITY_ID,
                transport_type=TransportTypeEnum.AIR,
                traveled_year=2020,
            ),
        )

    fake_journey_uow.commit_mock.assert_not_awaited()


async def test_update_journey_unknown_cities_rejected_before_transaction(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    fake_cities_client: FakeCitiesClient,
) -> None:
    """Города нет в geo → ``UnknownCityError`` с его id; транзакция не начиналась."""
    user_id = uuid4()
    journey_entity = make_journey(user_id=user_id)
    fake_journey_repository.journeys = [journey_entity]
    del fake_cities_client.locations[LONDON_CITY_ID]

    with pytest.raises(UnknownCityError) as exc_info:
        await journey_service.update_journey(
            user_id=user_id,
            journey_id=journey_entity.journey_id,
            command=UpdateJourneyCommand(
                origin_city_id=MOSCOW_CITY_ID,
                destination_city_id=LONDON_CITY_ID,
                transport_type=TransportTypeEnum.AIR,
                traveled_year=2020,
            ),
        )

    assert exc_info.value.details == {"city_ids": frozenset({LONDON_CITY_ID})}
    assert fake_journey_uow.transactions_started == 0


async def test_delete_journey_soft_deletes_and_commits(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
) -> None:
    """Поездка помечена удалённой и закоммичена."""
    user_id = uuid4()
    journey_entity = make_journey(user_id=user_id)
    fake_journey_repository.journeys = [journey_entity]

    await journey_service.delete_journey(user_id=user_id, journey_id=journey_entity.journey_id)

    assert fake_journey_repository.journeys[0].is_deleted
    fake_journey_uow.commit_mock.assert_awaited_once()


@pytest.mark.parametrize("case", ["missing", "foreign", "deleted"])
async def test_delete_journey_unavailable_journey_raises_not_found(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    case: str,
) -> None:
    """Несуществующая, чужая или уже удалённая поездка → ``JourneyNotFoundError`` без коммита."""
    user_id = uuid4()
    journey_entity = make_journey(
        user_id=uuid4() if case == "foreign" else user_id,
        deleted_at=_DELETED_AT if case == "deleted" else None,
    )
    if case != "missing":
        fake_journey_repository.journeys = [journey_entity]

    with pytest.raises(JourneyNotFoundError):
        await journey_service.delete_journey(user_id=user_id, journey_id=journey_entity.journey_id)

    fake_journey_uow.commit_mock.assert_not_awaited()


@pytest.mark.parametrize(
    ("neighbor_key", "placement", "lower", "upper"),
    [
        ("m", MovePlacementEnum.AFTER, "m", "t"),
        ("m", MovePlacementEnum.BEFORE, "c", "m"),
        ("t", MovePlacementEnum.AFTER, "t", None),
        ("c", MovePlacementEnum.BEFORE, None, "c"),
    ],
)
async def test_move_journey_places_key_between_neighbor_and_next_in_year(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    neighbor_key: str,
    placement: MovePlacementEnum,
    lower: str | None,
    upper: str | None,
) -> None:
    """Ключ строго между соседом и следующей строкой года с его стороны; на краю года — у края."""
    user_id = uuid4()
    year_entities = {key: make_journey(user_id=user_id, traveled_year=2020, sort_key=key) for key in ("c", "m", "t")}
    moved_entity = make_journey(user_id=user_id, traveled_year=2020, sort_key="x")
    fake_journey_repository.journeys = [*year_entities.values(), moved_entity]

    result = await journey_service.move_journey(
        user_id=user_id,
        journey_id=moved_entity.journey_id,
        command=MoveJourneyCommand(neighbor_journey_id=year_entities[neighbor_key].journey_id, placement=placement),
    )

    assert result == MoveJourneyResult(2020)
    assert lower is None or moved_entity.sort_key > lower
    assert upper is None or moved_entity.sort_key < upper
    fake_journey_uow.commit_mock.assert_awaited_once()


async def test_move_journey_into_another_year_takes_neighbor_year(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
) -> None:
    """Сосед из другого года: поездка получает его год, ключ — после соседа."""
    user_id = uuid4()
    neighbor_entity = make_journey(user_id=user_id, traveled_year=2018, sort_key="m")
    moved_entity = make_journey(user_id=user_id, traveled_year=2020, sort_key="m")
    fake_journey_repository.journeys = [neighbor_entity, moved_entity]

    result = await journey_service.move_journey(
        user_id=user_id,
        journey_id=moved_entity.journey_id,
        command=MoveJourneyCommand(neighbor_journey_id=neighbor_entity.journey_id, placement=MovePlacementEnum.AFTER),
    )

    assert result == MoveJourneyResult(2018)
    assert moved_entity.traveled_year == 2018
    assert moved_entity.sort_key > "m"


@pytest.mark.parametrize("case", ["missing", "foreign", "deleted", "self"])
async def test_move_journey_invalid_neighbor_raises_invalid_move_target(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    case: str,
) -> None:
    """Сосед несуществующий, чужой, удалённый или сама поездка → ``InvalidMoveTargetError`` без коммита."""
    user_id = uuid4()
    moved_entity = make_journey(user_id=user_id, sort_key="m")
    neighbor_entity = make_journey(
        user_id=uuid4() if case == "foreign" else user_id,
        deleted_at=_DELETED_AT if case == "deleted" else None,
    )
    fake_journey_repository.journeys = [moved_entity] if case == "missing" else [moved_entity, neighbor_entity]
    neighbor_journey_id = moved_entity.journey_id if case == "self" else neighbor_entity.journey_id

    with pytest.raises(InvalidMoveTargetError):
        await journey_service.move_journey(
            user_id=user_id,
            journey_id=moved_entity.journey_id,
            command=MoveJourneyCommand(neighbor_journey_id=neighbor_journey_id, placement=MovePlacementEnum.AFTER),
        )

    assert moved_entity.sort_key == "m"
    fake_journey_uow.commit_mock.assert_not_awaited()


async def test_move_journey_neighbor_repositioned_while_waiting_for_lock_uses_its_fresh_key(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
) -> None:
    """Соседа переставили, пока ждали блокировку года, — поездка встаёт рядом с его новым местом."""
    user_id = uuid4()
    neighbor_entity = make_journey(user_id=user_id, traveled_year=2020, sort_key="c")
    other_entity = make_journey(user_id=user_id, traveled_year=2020, sort_key="m")
    moved_entity = make_journey(user_id=user_id, traveled_year=2019, sort_key="m")
    fake_journey_repository.journeys = [neighbor_entity, other_entity, moved_entity]
    fake_journey_repository.journeys_after_lock = [
        make_journey(journey_id=neighbor_entity.journey_id, user_id=user_id, traveled_year=2020, sort_key="t"),
        other_entity,
        moved_entity,
    ]

    await journey_service.move_journey(
        user_id=user_id,
        journey_id=moved_entity.journey_id,
        command=MoveJourneyCommand(neighbor_journey_id=neighbor_entity.journey_id, placement=MovePlacementEnum.AFTER),
    )

    assert moved_entity.traveled_year == 2020
    assert moved_entity.sort_key > "t"


@pytest.mark.parametrize("case", ["another_year", "deleted"])
async def test_move_journey_neighbor_gone_while_waiting_for_lock_raises_invalid_move_target(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    case: str,
) -> None:
    """Соседа унесли в другой год или удалили, пока ждали блокировку, → ``InvalidMoveTargetError``."""
    user_id = uuid4()
    neighbor_entity = make_journey(user_id=user_id, traveled_year=2020, sort_key="c")
    moved_entity = make_journey(user_id=user_id, traveled_year=2019, sort_key="m")
    fake_journey_repository.journeys = [neighbor_entity, moved_entity]
    fake_journey_repository.journeys_after_lock = [
        make_journey(
            journey_id=neighbor_entity.journey_id,
            user_id=user_id,
            traveled_year=2018 if case == "another_year" else 2020,
            sort_key="c",
            deleted_at=_DELETED_AT if case == "deleted" else None,
        ),
        moved_entity,
    ]

    with pytest.raises(InvalidMoveTargetError):
        await journey_service.move_journey(
            user_id=user_id,
            journey_id=moved_entity.journey_id,
            command=MoveJourneyCommand(
                neighbor_journey_id=neighbor_entity.journey_id, placement=MovePlacementEnum.AFTER
            ),
        )

    assert (moved_entity.traveled_year, moved_entity.sort_key) == (2019, "m")
    fake_journey_uow.commit_mock.assert_not_awaited()


@pytest.mark.parametrize("case", ["missing", "deleted"])
async def test_move_journey_unavailable_journey_raises_not_found(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    case: str,
) -> None:
    """Переносимой поездки нет или она удалена → ``JourneyNotFoundError`` без коммита."""
    user_id = uuid4()
    neighbor_entity = make_journey(user_id=user_id)
    moved_entity = make_journey(user_id=user_id, deleted_at=_DELETED_AT)
    fake_journey_repository.journeys = [neighbor_entity] if case == "missing" else [neighbor_entity, moved_entity]

    with pytest.raises(JourneyNotFoundError):
        await journey_service.move_journey(
            user_id=user_id,
            journey_id=moved_entity.journey_id,
            command=MoveJourneyCommand(
                neighbor_journey_id=neighbor_entity.journey_id, placement=MovePlacementEnum.BEFORE
            ),
        )

    fake_journey_uow.commit_mock.assert_not_awaited()


async def test_list_journeys_maps_page_items_and_cursor(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
    fake_journey_uow: FakeJourneyUnitOfWork,
) -> None:
    """Строки страницы — поля поездок в порядке ленты, курсор следующей передан; чтение в транзакции."""
    user_id = uuid4()
    newer = make_journey(user_id=user_id, traveled_year=2021, sort_key="a", distance_km=10)
    older = make_journey(user_id=user_id, traveled_year=2019, sort_key="b", distance_km=20)
    fake_journey_repository.journeys = [older, newer, make_journey(user_id=user_id, traveled_year=2018)]

    result = await journey_service.list_journeys(
        user_id=user_id,
        command=ListJourneysCommand(
            page=CursorPageQuery(cursor=None, limit=2),
            filters=JourneyFilters(year_from=None, year_to=None, transport_types=None),
        ),
    )

    assert result.items == (
        JourneyFeedItem(
            journey_id=newer.journey_id,
            origin=newer.origin,
            destination=newer.destination,
            transport_type=newer.transport_type,
            traveled_year=2021,
            distance_km=10,
        ),
        JourneyFeedItem(
            journey_id=older.journey_id,
            origin=older.origin,
            destination=older.destination,
            transport_type=older.transport_type,
            traveled_year=2019,
            distance_km=20,
        ),
    )
    assert result.next_cursor is not None
    assert fake_journey_uow.transactions_started == 1


async def test_get_journey_years_returns_repository_years(
    journey_service: JourneyService,
    fake_journey_repository: FakeJourneyRepository,
    fake_journey_uow: FakeJourneyUnitOfWork,
) -> None:
    """Годы неудалённых поездок пользователя по возрастанию; чтение в транзакции."""
    user_id = uuid4()
    fake_journey_repository.journeys = [
        make_journey(user_id=user_id, traveled_year=2021),
        make_journey(user_id=user_id, traveled_year=2019),
        make_journey(user_id=user_id, traveled_year=2015, deleted_at=_DELETED_AT),
    ]

    result = await journey_service.get_journey_years(user_id)

    assert result == JourneyYearsResult((2019, 2021))
    assert fake_journey_uow.transactions_started == 1


async def test_estimate_journey_distance_uses_geo_coordinates(
    journey_service: JourneyService,
    fake_journey_uow: FakeJourneyUnitOfWork,
) -> None:
    """Москва → Лондон ≈ 2500 км по координатам geo; своих данных нет — без транзакции."""
    result = await journey_service.estimate_journey_distance(
        EstimateJourneyDistanceCommand(origin_city_id=MOSCOW_CITY_ID, destination_city_id=LONDON_CITY_ID),
    )

    assert result.distance_km == pytest.approx(2500, abs=60)
    assert fake_journey_uow.transactions_started == 0


async def test_estimate_journey_distance_unknown_city_raises_unknown_city(
    journey_service: JourneyService,
    fake_cities_client: FakeCitiesClient,
) -> None:
    """Города нет в geo → ``UnknownCityError`` с его id."""
    del fake_cities_client.locations[LONDON_CITY_ID]

    with pytest.raises(UnknownCityError) as exc_info:
        await journey_service.estimate_journey_distance(
            EstimateJourneyDistanceCommand(origin_city_id=MOSCOW_CITY_ID, destination_city_id=LONDON_CITY_ID),
        )

    assert exc_info.value.details == {"city_ids": frozenset({LONDON_CITY_ID})}
