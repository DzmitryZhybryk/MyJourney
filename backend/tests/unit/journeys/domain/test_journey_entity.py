"""Unit-тесты сущности ``JourneyEntity`` — новая поездка, правка, перенос и удаление."""

import datetime as dt
from uuid import uuid4

import pytest

from app.journeys.domain.entities import JourneyEntity
from app.journeys.domain.enums import TransportTypeEnum
from app.journeys.exceptions import JourneyNotFoundError
from tests.builders import LONDON_CITY_ID, MOSCOW_CITY_ID, make_geo_point, make_journey

_DELETED_AT = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def test_create_assigns_fields_and_mints_id() -> None:
    """create: чеканит собственный journey_id (uuid4) и прокидывает переданные поля."""
    user_id = uuid4()
    origin = make_geo_point(city_id=MOSCOW_CITY_ID, latitude=55.75, longitude=37.62)
    destination = make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12)

    journey_entity = JourneyEntity.create(
        user_id=user_id,
        origin=origin,
        destination=destination,
        transport_type=TransportTypeEnum.WATER,
        distance_km=2500,
        traveled_year=2019,
        sort_key="a1",
    )

    assert journey_entity.journey_id is not None
    assert journey_entity.user_id == user_id
    assert journey_entity.origin is origin
    assert journey_entity.destination is destination
    assert journey_entity.transport_type is TransportTypeEnum.WATER
    assert journey_entity.distance_km == 2500
    assert journey_entity.traveled_year == 2019
    assert journey_entity.sort_key == "a1"


def test_create_mints_distinct_ids_per_call() -> None:
    """create: каждый вызов чеканит новый идентификатор (id не переиспользуется)."""
    first = JourneyEntity.create(
        user_id=uuid4(),
        origin=make_geo_point(city_id=MOSCOW_CITY_ID, latitude=55.75, longitude=37.62),
        destination=make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12),
        transport_type=TransportTypeEnum.AIR,
        distance_km=2500,
        traveled_year=2020,
        sort_key="a1",
    )
    second = JourneyEntity.create(
        user_id=uuid4(),
        origin=make_geo_point(city_id=MOSCOW_CITY_ID, latitude=55.75, longitude=37.62),
        destination=make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12),
        transport_type=TransportTypeEnum.AIR,
        distance_km=2500,
        traveled_year=2020,
        sort_key="a1",
    )

    assert first.journey_id != second.journey_id


def test_revise_replaces_route_transport_and_distance_and_marks_updated() -> None:
    """revise: меняет города, транспорт и расстояние, ставит updated_at; год и ключ не трогает."""
    journey_entity = make_journey(traveled_year=2019, sort_key="a1", transport_type=TransportTypeEnum.AIR)
    origin = make_geo_point(city_id=uuid4(), country_code="FR", latitude=48.85, longitude=2.35)
    destination = make_geo_point(city_id=uuid4(), country_code="DE", latitude=52.52, longitude=13.4)
    started_at = dt.datetime.now(tz=dt.UTC)

    journey_entity.revise(
        origin=origin, destination=destination, transport_type=TransportTypeEnum.LAND, distance_km=880
    )

    assert journey_entity.origin is origin
    assert journey_entity.destination is destination
    assert journey_entity.transport_type is TransportTypeEnum.LAND
    assert journey_entity.distance_km == 880
    assert journey_entity.traveled_year == 2019
    assert journey_entity.sort_key == "a1"
    assert journey_entity.updated_at is not None
    assert journey_entity.updated_at >= started_at


def test_move_sets_year_and_sort_key_and_marks_updated() -> None:
    """move: ставит новый год и ключ вместе и обновляет updated_at."""
    journey_entity = make_journey(traveled_year=2019, sort_key="a1")
    started_at = dt.datetime.now(tz=dt.UTC)

    journey_entity.move(traveled_year=2021, sort_key="b5")

    assert journey_entity.traveled_year == 2021
    assert journey_entity.sort_key == "b5"
    assert journey_entity.updated_at is not None
    assert journey_entity.updated_at >= started_at


def test_delete_marks_deleted_at_and_updated_at_with_one_moment() -> None:
    """delete: soft-delete — deleted_at и updated_at выставлены одним моментом."""
    journey_entity = make_journey()

    journey_entity.delete()

    assert journey_entity.is_deleted
    assert journey_entity.deleted_at is not None
    assert journey_entity.updated_at == journey_entity.deleted_at


def test_ensure_not_deleted_passes_for_live_journey() -> None:
    """ensure_not_deleted: неудалённая поездка проходит без ошибки."""
    make_journey().ensure_not_deleted()


def test_ensure_not_deleted_raises_for_deleted_journey() -> None:
    """ensure_not_deleted: удалённая поездка → JourneyNotFoundError."""
    journey_entity = make_journey(deleted_at=_DELETED_AT)

    with pytest.raises(JourneyNotFoundError):
        journey_entity.ensure_not_deleted()
