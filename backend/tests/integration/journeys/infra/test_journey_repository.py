"""
Интеграционные тесты ``JourneyRepository`` против реального Postgres.

Покрывают то, что нельзя проверить на фейках: round-trip сущность→модель (денормализованный
снапшот origin/destination, дата+точность, distance_km через REAL), вставку нескольких
поездок одного пользователя (на ``user_id`` нет unique-констрейнта) и правила выборок для
карт — они целиком живут в SQL: города и годы для карты и глобуса, маршруты и окно фильтров
для карты перемещений, годы первой и последней поездки. Порядок ленты и курсор, фильтры,
побайтное сравнение ключей (``COLLATE "C"``), частичный unique-индекс, advisory-блокировка
области и запись правки/переноса/удаления.
"""

import asyncio
import datetime as dt
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.journeys.application.ports.journey_repository import JourneyFilters, JourneyOrderScope
from app.journeys.domain.entities import JourneyEntity
from app.journeys.domain.enums import TransportTypeEnum
from app.journeys.infra.models import Journey
from app.journeys.infra.repositories import JourneyRepository
from app.shared.fractional_index import generate_key_between
from app.shared.pagination import PageQuery
from tests.builders import (
    LONDON_CITY_ID,
    MOSCOW_CITY_ID,
    make_geo_point,
    make_journey,
)

_PARIS_CITY_ID = UUID("33333333-3333-4333-8333-333333333333")
_MOSCOW = make_geo_point(city_id=MOSCOW_CITY_ID, country_code="RU", latitude=55.75, longitude=37.62)
_LONDON = make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12)
_PARIS = make_geo_point(city_id=_PARIS_CITY_ID, country_code="FR", latitude=48.85, longitude=2.35)
_DELETED_AT = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
_NO_FILTERS = JourneyFilters(year_from=None, year_to=None, transport_types=None)
# Есть ли сессия, ждущая advisory-блокировку, — условие, которого ждёт тест параллельных вставок.
_WAITING_ADVISORY_LOCKS = sa.text("SELECT count(*) > 0 FROM pg_locks WHERE locktype = 'advisory' AND NOT granted")
_LOCK_WAIT_TIMEOUT_SECONDS = 5
_LOCK_POLL_SECONDS = 0.02


async def _insert(db_session: AsyncSession, *journey_entities: JourneyEntity) -> JourneyRepository:
    repository = JourneyRepository(session=db_session)
    for journey_entity in journey_entities:
        await repository.insert_journey(journey_entity=journey_entity)

    await db_session.commit()
    return repository


async def test_insert_journey_persists_snapshot(db_session: AsyncSession) -> None:
    """insert_journey: сущность ложится в плоский снапшот — города/страны/координаты, год, distance_km."""
    user_id = uuid4()
    journey_entity = make_journey(
        user_id=user_id,
        transport_type=TransportTypeEnum.AIR,
        traveled_year=2020,
    )

    await JourneyRepository(session=db_session).insert_journey(journey_entity=journey_entity)
    await db_session.commit()

    journey_model = (await db_session.execute(sa.select(Journey))).scalar_one()
    assert journey_model.id == journey_entity.journey_id
    assert journey_model.user_id == user_id
    assert journey_model.origin_city_id == MOSCOW_CITY_ID
    assert journey_model.origin_country_code == "RU"
    assert journey_model.destination_city_id == LONDON_CITY_ID
    assert journey_model.destination_country_code == "GB"
    assert journey_model.transport_type == "air"
    assert journey_model.traveled_year == 2020
    assert journey_model.distance_km == pytest.approx(2500, abs=60)
    assert journey_model.origin_latitude == pytest.approx(55.75, abs=0.01)


async def test_insert_multiple_journeys_for_same_user(db_session: AsyncSession) -> None:
    """insert_journey: несколько поездок одного пользователя сохраняются (на user_id нет unique)."""
    user_id = uuid4()
    repository = JourneyRepository(session=db_session)

    await repository.insert_journey(journey_entity=make_journey(user_id=user_id))
    await repository.insert_journey(journey_entity=make_journey(user_id=user_id))
    await db_session.commit()

    count = (await db_session.execute(sa.select(sa.func.count()).select_from(Journey))).scalar_one()
    assert count == 2


# --- find_visited_cities_by_user_id ---------------------------------------------------------


async def test_find_visited_cities_counts_both_ends_with_distinct_sorted_years(db_session: AsyncSession) -> None:
    """Города — и отправления, и назначения, по одной строке; годы без повторов и по возрастанию."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON, traveled_year=2021),
        make_journey(user_id=user_id, origin=_LONDON, destination=_MOSCOW, traveled_year=2019),
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON, traveled_year=2021),
    )

    visited_cities = await repository.find_visited_cities_by_user_id(user_id=user_id)

    years_by_city = {visited_city.city.city_id: visited_city.years for visited_city in visited_cities}
    assert years_by_city == {MOSCOW_CITY_ID: (2019, 2021), LONDON_CITY_ID: (2019, 2021)}


async def test_find_visited_cities_orders_by_country_then_city_id(db_session: AsyncSession) -> None:
    """Порядок — по коду страны, внутри страны по city_id: города одной страны идут подряд."""
    user_id = uuid4()
    second_moscow_id = UUID("00000000-0000-4000-8000-000000000001")
    second_russian_city = make_geo_point(city_id=second_moscow_id, country_code="RU", latitude=59.9, longitude=30.3)
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_PARIS),
        make_journey(user_id=user_id, origin=_LONDON, destination=second_russian_city),
    )

    visited_cities = await repository.find_visited_cities_by_user_id(user_id=user_id)

    assert [(visited_city.city.country_code, visited_city.city.city_id) for visited_city in visited_cities] == [
        ("FR", _PARIS_CITY_ID),
        ("GB", LONDON_CITY_ID),
        ("RU", min(MOSCOW_CITY_ID, second_moscow_id)),
        ("RU", max(MOSCOW_CITY_ID, second_moscow_id)),
    ]


async def test_find_visited_cities_diverging_copies_of_city_give_one_row(db_session: AsyncSession) -> None:
    """Копии города с разными координатами (справочник обновился) — одна строка, координаты одной копии целиком."""
    user_id = uuid4()
    shifted_moscow = make_geo_point(city_id=MOSCOW_CITY_ID, country_code="RU", latitude=55.7, longitude=37.7)
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON),
        make_journey(user_id=user_id, origin=shifted_moscow, destination=_PARIS),
    )

    visited_cities = await repository.find_visited_cities_by_user_id(user_id=user_id)

    moscow_rows = [visited_city for visited_city in visited_cities if visited_city.city.city_id == MOSCOW_CITY_ID]
    assert len(moscow_rows) == 1
    point = (moscow_rows[0].city.latitude, moscow_rows[0].city.longitude)
    assert point in [
        (pytest.approx(_MOSCOW.latitude, abs=0.001), pytest.approx(_MOSCOW.longitude, abs=0.001)),
        (pytest.approx(55.7, abs=0.001), pytest.approx(37.7, abs=0.001)),
    ]


async def test_find_visited_cities_skips_deleted_and_other_users_journeys(db_session: AsyncSession) -> None:
    """Удалённые поездки и поездки другого пользователя в выборку не попадают."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON),
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_PARIS, deleted_at=_DELETED_AT),
        make_journey(user_id=uuid4(), origin=_PARIS, destination=_LONDON),
    )

    visited_cities = await repository.find_visited_cities_by_user_id(user_id=user_id)

    assert {visited_city.city.city_id for visited_city in visited_cities} == {MOSCOW_CITY_ID, LONDON_CITY_ID}


async def test_find_visited_cities_without_journeys_returns_empty(db_session: AsyncSession) -> None:
    """У пользователя без поездок городов нет."""
    assert await JourneyRepository(session=db_session).find_visited_cities_by_user_id(user_id=uuid4()) == ()


# --- find_movement_connections_by_user_id ---------------------------------------------------


async def test_find_movement_connections_one_row_per_directed_route(db_session: AsyncSession) -> None:
    """Повторы маршрута — одна строка, обратный маршрут — отдельная; порядок по city_id концов."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON),
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON),
        make_journey(user_id=user_id, origin=_LONDON, destination=_MOSCOW),
        make_journey(user_id=user_id, origin=_LONDON, destination=_PARIS),
    )

    connections = await repository.find_movement_connections_by_user_id(user_id=user_id, transport_types=None)

    routes = [(connection.origin.city_id, connection.destination.city_id) for connection in connections]
    assert routes == sorted(
        [(MOSCOW_CITY_ID, LONDON_CITY_ID), (LONDON_CITY_ID, MOSCOW_CITY_ID), (LONDON_CITY_ID, _PARIS_CITY_ID)]
    )
    moscow_to_london = connections[routes.index((MOSCOW_CITY_ID, LONDON_CITY_ID))]
    assert moscow_to_london.origin.latitude == pytest.approx(55.75, abs=0.001)
    assert moscow_to_london.destination.country_code == "GB"


async def test_find_movement_connections_carry_distinct_sorted_years(db_session: AsyncSession) -> None:
    """У маршрута — годы его поездок без повторов и по возрастанию; годы обратного маршрута — его собственные."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON, traveled_year=2021),
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON, traveled_year=2018),
        make_journey(
            user_id=user_id,
            origin=_MOSCOW,
            destination=_LONDON,
            traveled_year=2021,
        ),
        make_journey(user_id=user_id, origin=_LONDON, destination=_MOSCOW, traveled_year=2019),
    )

    connections = await repository.find_movement_connections_by_user_id(user_id=user_id, transport_types=None)

    years_by_route = {
        (connection.origin.city_id, connection.destination.city_id): connection.years for connection in connections
    }
    assert years_by_route == {
        (MOSCOW_CITY_ID, LONDON_CITY_ID): (2018, 2021),
        (LONDON_CITY_ID, MOSCOW_CITY_ID): (2019,),
    }


async def test_find_movement_connections_years_only_from_selected_transport(db_session: AsyncSession) -> None:
    """Годы маршрута — только из поездок на выбранном транспорте: другие виды их не добавляют."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(
            user_id=user_id,
            origin=_MOSCOW,
            destination=_LONDON,
            transport_type=TransportTypeEnum.AIR,
            traveled_year=2019,
        ),
        make_journey(
            user_id=user_id,
            origin=_MOSCOW,
            destination=_LONDON,
            transport_type=TransportTypeEnum.LAND,
            traveled_year=2022,
        ),
    )

    [connection] = await repository.find_movement_connections_by_user_id(
        user_id=user_id, transport_types=frozenset({TransportTypeEnum.AIR})
    )

    assert connection.years == (2019,)


async def test_find_movement_connections_filters_by_transport(db_session: AsyncSession) -> None:
    """Учитываются только поездки на выбранных видах транспорта; None — все виды."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON, transport_type=TransportTypeEnum.AIR),
        make_journey(user_id=user_id, origin=_LONDON, destination=_PARIS, transport_type=TransportTypeEnum.LAND),
        make_journey(user_id=user_id, origin=_PARIS, destination=_MOSCOW, transport_type=TransportTypeEnum.WATER),
    )

    async def destinations(transport_types: frozenset[TransportTypeEnum] | None) -> set[UUID]:
        connections = await repository.find_movement_connections_by_user_id(
            user_id=user_id, transport_types=transport_types
        )
        return {connection.destination.city_id for connection in connections}

    assert await destinations(frozenset({TransportTypeEnum.AIR, TransportTypeEnum.WATER})) == {
        LONDON_CITY_ID,
        MOSCOW_CITY_ID,
    }
    assert await destinations(None) == {LONDON_CITY_ID, _PARIS_CITY_ID, MOSCOW_CITY_ID}


async def test_find_movement_connections_skips_deleted_and_other_users_journeys(db_session: AsyncSession) -> None:
    """Удалённые поездки и поездки другого пользователя маршрутов не дают."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, origin=_MOSCOW, destination=_LONDON),
        make_journey(user_id=user_id, origin=_LONDON, destination=_PARIS, deleted_at=_DELETED_AT),
        make_journey(user_id=uuid4(), origin=_PARIS, destination=_MOSCOW),
    )

    connections = await repository.find_movement_connections_by_user_id(user_id=user_id, transport_types=None)

    assert [(connection.origin.city_id, connection.destination.city_id) for connection in connections] == [
        (MOSCOW_CITY_ID, LONDON_CITY_ID)
    ]


async def test_find_movement_connections_without_journeys_returns_empty(db_session: AsyncSession) -> None:
    """У пользователя без поездок маршрутов нет."""
    connections = await JourneyRepository(session=db_session).find_movement_connections_by_user_id(
        user_id=uuid4(), transport_types=None
    )

    assert connections == ()


# --- find_journey_years_by_user_id ----------------------------------------------------------


async def test_find_journey_years_returns_distinct_years_ascending(db_session: AsyncSession) -> None:
    """Годы неудалённых поездок самого пользователя — без повторов, по возрастанию."""
    user_id = uuid4()
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, traveled_year=2021),
        make_journey(user_id=user_id, traveled_year=2017),
        make_journey(user_id=user_id, traveled_year=2019),
        make_journey(user_id=user_id, traveled_year=2017),
        make_journey(user_id=user_id, traveled_year=2023, deleted_at=_DELETED_AT),
        make_journey(user_id=uuid4(), traveled_year=2010),
    )

    assert await repository.find_journey_years_by_user_id(user_id=user_id) == (2017, 2019, 2021)


async def test_find_journey_years_without_journeys_returns_empty(db_session: AsyncSession) -> None:
    """Поездок нет (или все удалены) — лет нет."""
    user_id = uuid4()
    repository = await _insert(db_session, make_journey(user_id=user_id, deleted_at=_DELETED_AT))

    assert await repository.find_journey_years_by_user_id(user_id=user_id) == ()
    assert await repository.find_journey_years_by_user_id(user_id=uuid4()) == ()


# --- find_journeys_page_by_user_id ---------------------------------------------------------


async def test_find_journeys_page_orders_fresh_year_first_then_sort_key(db_session: AsyncSession) -> None:
    """Лента: год по убыванию, внутри года — по ключу; удалённые и чужие поездки не попадают."""
    user_id = uuid4()
    late_2021 = make_journey(user_id=user_id, traveled_year=2021, sort_key="t")
    early_2021 = make_journey(user_id=user_id, traveled_year=2021, sort_key="c")
    only_2019 = make_journey(user_id=user_id, traveled_year=2019, sort_key="a")
    repository = await _insert(
        db_session,
        only_2019,
        late_2021,
        early_2021,
        make_journey(user_id=user_id, traveled_year=2021, sort_key="m", deleted_at=_DELETED_AT),
        make_journey(user_id=uuid4(), traveled_year=2022),
    )

    page = await repository.find_journeys_page_by_user_id(
        user_id=user_id,
        page=PageQuery(cursor=None, limit=10),
        filters=_NO_FILTERS,
    )

    assert [journey.journey_id for journey in page.items] == [
        early_2021.journey_id,
        late_2021.journey_id,
        only_2019.journey_id,
    ]
    assert page.next_cursor is None


async def test_find_journeys_page_cursor_walks_whole_feed_without_gaps(db_session: AsyncSession) -> None:
    """Курсор: страницы по 2 строки складываются в ту же ленту без пропусков и повторов, в т.ч. на стыке лет."""
    user_id = uuid4()
    journey_entities = [
        make_journey(user_id=user_id, traveled_year=year, sort_key=key)
        for year, key in [(2022, "b"), (2022, "k"), (2022, "x"), (2020, "a"), (2020, "c"), (2018, "q")]
    ]
    repository = await _insert(db_session, *journey_entities)

    walked: list[UUID] = []
    cursor: str | None = None
    while True:
        page = await repository.find_journeys_page_by_user_id(
            user_id=user_id,
            page=PageQuery(cursor=cursor, limit=2),
            filters=_NO_FILTERS,
        )
        walked.extend(journey.journey_id for journey in page.items)
        if page.next_cursor is None:
            break

        cursor = page.next_cursor

    assert walked == [journey.journey_id for journey in journey_entities]


async def test_find_journeys_page_filters_by_year_range_and_transport(db_session: AsyncSession) -> None:
    """Фильтр: годы включительно с обеих сторон и набор видов транспорта."""
    user_id = uuid4()
    in_range_air = make_journey(user_id=user_id, traveled_year=2020, transport_type=TransportTypeEnum.AIR)
    edge_water = make_journey(user_id=user_id, traveled_year=2018, transport_type=TransportTypeEnum.WATER)
    repository = await _insert(
        db_session,
        in_range_air,
        edge_water,
        make_journey(user_id=user_id, traveled_year=2019, transport_type=TransportTypeEnum.LAND),
        make_journey(user_id=user_id, traveled_year=2021, transport_type=TransportTypeEnum.AIR),
        make_journey(user_id=user_id, traveled_year=2017, transport_type=TransportTypeEnum.WATER),
    )

    page = await repository.find_journeys_page_by_user_id(
        user_id=user_id,
        page=PageQuery(cursor=None, limit=10),
        filters=JourneyFilters(
            year_from=2018,
            year_to=2020,
            transport_types=frozenset({TransportTypeEnum.AIR, TransportTypeEnum.WATER}),
        ),
    )

    assert [journey.journey_id for journey in page.items] == [in_range_air.journey_id, edge_water.journey_id]


async def test_find_journeys_page_sort_key_compares_bytewise(db_session: AsyncSession) -> None:
    """COLLATE "C": «Zz» раньше «a1» (побайтно), а не после (по правилам языка); последний ключ — «a1»."""
    user_id = uuid4()
    upper = make_journey(user_id=user_id, traveled_year=2020, sort_key="Zz")
    lower = make_journey(user_id=user_id, traveled_year=2020, sort_key="a1")
    repository = await _insert(db_session, lower, upper)

    page = await repository.find_journeys_page_by_user_id(
        user_id=user_id,
        page=PageQuery(cursor=None, limit=10),
        filters=_NO_FILTERS,
    )

    assert [journey.sort_key for journey in page.items] == ["Zz", "a1"]
    assert await repository.find_last_sort_key(scope=JourneyOrderScope(user_id=user_id, traveled_year=2020)) == "a1"


# --- порядок внутри года: соседние ключи, уникальность, блокировка ------------------------------


async def test_find_next_and_previous_sort_key_stay_in_live_rows_of_year(db_session: AsyncSession) -> None:
    """Следующий/предыдущий ключ — только среди неудалённых поездок того же года пользователя; на краю — None."""
    user_id = uuid4()
    scope = JourneyOrderScope(user_id=user_id, traveled_year=2020)
    repository = await _insert(
        db_session,
        make_journey(user_id=user_id, traveled_year=2020, sort_key="c"),
        make_journey(user_id=user_id, traveled_year=2020, sort_key="m"),
        make_journey(user_id=user_id, traveled_year=2020, sort_key="f", deleted_at=_DELETED_AT),
        make_journey(user_id=user_id, traveled_year=2021, sort_key="e"),
        make_journey(user_id=uuid4(), traveled_year=2020, sort_key="d"),
    )

    assert await repository.find_next_sort_key(scope=scope, after_sort_key="c") == "m"
    assert await repository.find_previous_sort_key(scope=scope, before_sort_key="m") == "c"
    assert await repository.find_next_sort_key(scope=scope, after_sort_key="m") is None
    assert await repository.find_previous_sort_key(scope=scope, before_sort_key="c") is None


async def test_unique_sort_key_index_rejects_duplicate_live_key_in_year(db_session: AsyncSession) -> None:
    """Частичный unique-индекс: два живых ключа в одном году пользователя — IntegrityError."""
    user_id = uuid4()
    repository = JourneyRepository(session=db_session)
    await repository.insert_journey(journey_entity=make_journey(user_id=user_id, traveled_year=2020, sort_key="m"))
    await repository.insert_journey(journey_entity=make_journey(user_id=user_id, traveled_year=2020, sort_key="m"))

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_unique_sort_key_index_ignores_deleted_rows(db_session: AsyncSession) -> None:
    """Удалённая поездка не держит свой ключ: живая с тем же ключом в том же году сохраняется."""
    user_id = uuid4()
    await _insert(
        db_session,
        make_journey(user_id=user_id, traveled_year=2020, sort_key="m", deleted_at=_DELETED_AT),
        make_journey(user_id=user_id, traveled_year=2020, sort_key="m"),
    )

    count = (await db_session.execute(sa.select(sa.func.count()).select_from(Journey))).scalar_one()
    assert count == 2


async def test_lock_sort_keys_serializes_concurrent_inserts_into_one_year(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Две параллельные вставки в один год: вторая ждёт блокировку первой и получает ключ после её ключа."""
    user_id = uuid4()
    scope = JourneyOrderScope(user_id=user_id, traveled_year=2020)
    async with session_factory() as first_session, session_factory() as second_session:
        first_repository = JourneyRepository(session=first_session)
        second_repository = JourneyRepository(session=second_session)
        await first_repository.lock_sort_keys(scope=scope)
        first_key = generate_key_between(before=await first_repository.find_last_sort_key(scope=scope), after=None)

        async def insert_second() -> str:
            await second_repository.lock_sort_keys(scope=scope)
            second_key = generate_key_between(
                before=await second_repository.find_last_sort_key(scope=scope),
                after=None,
            )
            await second_repository.insert_journey(
                journey_entity=make_journey(user_id=user_id, traveled_year=2020, sort_key=second_key)
            )
            await second_session.commit()
            return second_key

        second_task = asyncio.create_task(insert_second())
        # Ждём, пока вторая сессия действительно встанет в очередь за блокировкой первой. Это
        # состояние Postgres, а не событие процесса, — asyncio.Event его не увидит, только опрос.
        async with session_factory() as observer_session:
            async with asyncio.timeout(_LOCK_WAIT_TIMEOUT_SECONDS):
                while not await observer_session.scalar(_WAITING_ADVISORY_LOCKS):  # noqa: ASYNC110
                    await asyncio.sleep(_LOCK_POLL_SECONDS)

        await first_repository.insert_journey(
            journey_entity=make_journey(user_id=user_id, traveled_year=2020, sort_key=first_key)
        )
        await first_session.commit()
        second_key = await asyncio.wait_for(second_task, timeout=_LOCK_WAIT_TIMEOUT_SECONDS)

    assert second_key > first_key


# --- правка, перенос, удаление -----------------------------------------------------------------


async def test_update_journey_by_id_persists_revise_and_move(db_session: AsyncSession) -> None:
    """update_journey_by_id: новые города, транспорт, расстояние, год и ключ ложатся в строку."""
    user_id = uuid4()
    journey_entity = make_journey(
        user_id=user_id, traveled_year=2020, sort_key="m", transport_type=TransportTypeEnum.AIR
    )
    repository = await _insert(db_session, journey_entity)

    journey_entity.revise(origin=_PARIS, destination=_MOSCOW, transport_type=TransportTypeEnum.LAND, distance_km=2480)
    journey_entity.move(traveled_year=2018, sort_key="b")
    await repository.update_journey_by_id(journey_entity=journey_entity)
    await db_session.commit()

    stored = await repository.find_journey_by_id_and_user_id(journey_id=journey_entity.journey_id, user_id=user_id)
    assert stored is not None
    assert stored.origin.city_id == _PARIS_CITY_ID
    assert stored.destination.city_id == MOSCOW_CITY_ID
    assert stored.transport_type is TransportTypeEnum.LAND
    assert stored.distance_km == 2480
    assert stored.traveled_year == 2018
    assert stored.sort_key == "b"
    assert stored.updated_at is not None


async def test_deleted_journey_drops_out_of_feed_and_years_but_stays_findable(db_session: AsyncSession) -> None:
    """Удалённая поездка: пропадает из ленты и лет, но точечный поиск её отдаёт (решает сервис)."""
    user_id = uuid4()
    journey_entity = make_journey(user_id=user_id, traveled_year=2020)
    repository = await _insert(db_session, journey_entity)

    journey_entity.delete()
    await repository.update_journey_by_id(journey_entity=journey_entity)
    await db_session.commit()

    page = await repository.find_journeys_page_by_user_id(
        user_id=user_id,
        page=PageQuery(cursor=None, limit=10),
        filters=_NO_FILTERS,
    )
    stored = await repository.find_journey_by_id_and_user_id(journey_id=journey_entity.journey_id, user_id=user_id)
    assert page.items == ()
    assert await repository.find_journey_years_by_user_id(user_id=user_id) == ()
    assert stored is not None
    assert stored.is_deleted


async def test_find_journey_by_id_and_user_id_hides_other_users_journey(db_session: AsyncSession) -> None:
    """Поездка другого пользователя по её id не находится — ни обычным, ни блокирующим поиском."""
    journey_entity = make_journey(user_id=uuid4())
    repository = await _insert(db_session, journey_entity)

    assert (
        await repository.find_journey_by_id_and_user_id(journey_id=journey_entity.journey_id, user_id=uuid4()) is None
    )
    assert (
        await repository.find_journey_by_id_and_user_id_for_update(
            journey_id=journey_entity.journey_id,
            user_id=uuid4(),
        )
        is None
    )
