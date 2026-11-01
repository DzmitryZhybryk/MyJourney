"""
api-тесты роутов journeys (``POST``/``GET /v1/journeys/``, ``PUT``/``DELETE /{id}/``, ``/{id}/move/``,
``/years/``, ``/distance/``, ``/map/``, ``/globe/``, ``/movements/``) на ASGI-приложении.

Реальная проводка ``journey_service`` поверх фейк-UoW, реальный декод Bearer-токена
(``mint_access_token`` подписывает settings-секретом; ``sub`` токена становится ``user_id``
поездки). Пиннят 201-payload-on-create, 401 без токена, 400 неизвестного города, 422 запроса,
сериализацию ответов карт (camelCase, без лишних полей) и то, что фильтры карты перемещений
из query доходят до репозитория.
"""

import datetime as dt
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.geo.presentation.dependencies import geo_uow_dependency
from app.journeys.application.ports.journey_repository import MovementConnection, VisitedCity
from app.journeys.domain.enums import TransportTypeEnum
from app.journeys.presentation.dependencies import cities_client_dependency
from app.shared.schemas.base import BFastAPI
from tests.builders import (
    LONDON_CITY_ID,
    MOSCOW_CITY_ID,
    make_city,
    make_geo_point,
    make_journey,
)
from tests.fakes import (
    FakeCitiesClient,
    FakeCityRepository,
    FakeGeoUnitOfWork,
    FakeJourneyRepository,
    FakeJourneyUnitOfWork,
    MovementConnectionQuery,
)

_CREATE_PATH = "/v1/journeys/"
_MAP_PATH = "/v1/journeys/map/"
_GLOBE_PATH = "/v1/journeys/globe/"
_MOVEMENTS_PATH = "/v1/journeys/movements/"
_FEED_PATH = "/v1/journeys/"
_YEARS_PATH = "/v1/journeys/years/"
_DISTANCE_PATH = "/v1/journeys/distance/"
_ROUTE = {"originCityId": str(MOSCOW_CITY_ID), "destinationCityId": str(LONDON_CITY_ID)}
_VALID_BODY: dict[str, Any] = {
    **_ROUTE,
    "transportType": "air",
    "traveledYear": 2020,
}
_CURRENT_YEAR = dt.datetime.now(tz=dt.UTC).year


async def test_create_journey_returns_201_and_persists(
    client: AsyncClient,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """201: поездка под user_id из токена, страна и координаты городов — из geo; тело пустое, commit один раз."""
    user_id = uuid4()

    response = await client.post(
        _CREATE_PATH,
        json=_VALID_BODY,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"},
    )

    assert response.status_code == 201
    assert response.content == b""
    assert len(fake_journey_repository.journeys) == 1
    journey_entity = fake_journey_repository.journeys[0]
    assert journey_entity.user_id == user_id
    assert journey_entity.origin.city_id == MOSCOW_CITY_ID
    assert journey_entity.destination.city_id == LONDON_CITY_ID
    assert journey_entity.destination.country_code == "GB"
    assert journey_entity.destination.latitude == pytest.approx(51.5)
    assert journey_entity.transport_type is TransportTypeEnum.AIR
    assert journey_entity.traveled_year == 2020
    fake_journey_uow.commit_mock.assert_awaited_once()


async def test_create_journey_current_year_returns_201(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """201: текущий год (по UTC) — граница «не в будущем», поездка создаётся."""
    response = await client.post(
        _CREATE_PATH,
        json={**_VALID_BODY, "traveledYear": _CURRENT_YEAR},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 201
    assert fake_journey_repository.journeys[0].traveled_year == _CURRENT_YEAR


async def test_create_journey_ignores_legacy_month_and_day(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """201: присланные старым клиентом traveledMonth/traveledDay игнорируются, сохраняется только год."""
    response = await client.post(
        _CREATE_PATH,
        json={**_VALID_BODY, "traveledMonth": 6, "traveledDay": 15},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 201
    assert fake_journey_repository.journeys[0].traveled_year == 2020


async def test_create_journey_without_token_returns_401(client: AsyncClient) -> None:
    """401: запрос без Bearer-токена отклоняется с кодом auth.invalid_access_token."""
    response = await client.post(_CREATE_PATH, json=_VALID_BODY)

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


@pytest.mark.parametrize(
    ("overrides", "expected_code", "expected_field"),
    [
        ({"destinationCityId": str(MOSCOW_CITY_ID)}, "journeys.same_origin_destination", None),
        ({"traveledYear": _CURRENT_YEAR + 1}, "journeys.date_in_future", "year"),
    ],
)
async def test_create_journey_rejected_by_request_rules_returns_400(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
    overrides: dict[str, Any],
    expected_code: str,
    expected_field: str | None,
) -> None:
    """400: правила схемы запроса отдают свой код journeys.*, а не общий 422; поездка не создаётся."""
    response = await client.post(
        _CREATE_PATH,
        json={**_VALID_BODY, **overrides},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    body = response.json()
    assert response.status_code == 400
    assert body["code"] == expected_code
    assert (body.get("details") or {}).get("field") == expected_field
    assert fake_journey_repository.journeys == []


async def test_create_journey_year_below_one_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """422: год меньше 1 — ограничение поля, общий validation_error."""
    response = await client.post(
        _CREATE_PATH,
        json={**_VALID_BODY, "traveledYear": 0},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_create_journey_unknown_city_returns_400_with_missing_ids(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    fake_cities_client: FakeCitiesClient,
    mint_access_token: Callable[..., str],
) -> None:
    """400: города нет в geo → journeys.unknown_city, ненайденные id в details.city_ids, поездка не создана."""
    del fake_cities_client.locations[LONDON_CITY_ID]

    response = await client.post(
        _CREATE_PATH,
        json=_VALID_BODY,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "journeys.unknown_city"
    assert body["details"] == {"city_ids": [str(LONDON_CITY_ID)]}
    assert fake_journey_repository.journeys == []


async def test_create_journey_checks_cities_through_real_geo_wiring(
    app: BFastAPI,
    make_async_client: Callable[[BFastAPI], AsyncClient],
    fake_journey_repository: FakeJourneyRepository,
    fake_city_repository: FakeCityRepository,
    fake_geo_uow: FakeGeoUnitOfWork,
    mint_access_token: Callable[..., str],
) -> None:
    """400: без подмены клиента городов проверка идёт через настоящую цепочку journeys → geo до UoW geo."""
    app.dependency_overrides.pop(cities_client_dependency)
    app.dependency_overrides[geo_uow_dependency] = lambda: fake_geo_uow
    fake_city_repository.cities.append(make_city(city_id=MOSCOW_CITY_ID))

    async with make_async_client(app) as client:
        response = await client.post(
            _CREATE_PATH,
            json=_VALID_BODY,
            headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
        )

    assert response.status_code == 400
    assert response.json()["details"] == {"city_ids": [str(LONDON_CITY_ID)]}
    assert fake_journey_repository.journeys == []


async def test_create_journey_pre_rename_body_returns_422(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """422: тело клиента до переименования (originPlaceId/destinationPlaceId) отклоняется, а не принимается молча."""
    response = await client.post(
        _CREATE_PATH,
        json={
            "originPlaceId": str(MOSCOW_CITY_ID),
            "destinationPlaceId": str(LONDON_CITY_ID),
            "transportType": "air",
            "traveledYear": 2020,
        },
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert fake_journey_repository.journeys == []


async def test_get_journeys_map_returns_aggregated_countries(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: агрегат карты сериализуется в camelCase — страны по коду, города с координатами и годами."""
    user_id = uuid4()
    fake_journey_repository.visited_cities_by_user_id[user_id] = [
        VisitedCity(
            city=make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12),
            years=(2020,),
        ),
        VisitedCity(
            city=make_geo_point(city_id=MOSCOW_CITY_ID, country_code="RU", latitude=55.75, longitude=37.62),
            years=(2020,),
        ),
    ]

    response = await client.get(_MAP_PATH, headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"})

    assert response.status_code == 200
    body = response.json()
    assert [country["countryCode"] for country in body["countries"]] == ["GB", "RU"]
    london = body["countries"][0]["cities"][0]
    assert london["cityId"] == str(LONDON_CITY_ID)
    assert set(london) == {"cityId", "latitude", "longitude", "years"}
    assert london["years"] == [2020]
    assert london["latitude"] == pytest.approx(51.5)
    assert london["longitude"] == pytest.approx(-0.12)


async def test_get_journeys_map_without_token_returns_401(client: AsyncClient) -> None:
    """401: запрос карты без Bearer-токена отклоняется кодом auth.invalid_access_token."""
    response = await client.get(_MAP_PATH)

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_get_journeys_map_without_journeys_returns_empty(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """200: у пользователя без поездок карта отдаёт пустой список стран."""
    response = await client.get(_MAP_PATH, headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"})

    assert response.status_code == 200
    assert response.json() == {"countries": []}


async def test_get_journeys_globe_returns_cities_without_country(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: глобус получает города в camelCase — id и координаты, без страны и годов."""
    user_id = uuid4()
    fake_journey_repository.visited_cities_by_user_id[user_id] = [
        VisitedCity(
            city=make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12),
            years=(2020,),
        ),
    ]

    response = await client.get(_GLOBE_PATH, headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"})

    assert response.status_code == 200
    [city] = response.json()["cities"]
    assert set(city) == {"cityId", "latitude", "longitude"}
    assert city["cityId"] == str(LONDON_CITY_ID)
    assert city["latitude"] == pytest.approx(51.5)


async def test_get_journeys_globe_without_journeys_returns_empty(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """200: у пользователя без поездок глобус отдаёт пустой список городов."""
    response = await client.get(_GLOBE_PATH, headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"})

    assert response.status_code == 200
    assert response.json() == {"cities": []}


@pytest.mark.parametrize("path", [_GLOBE_PATH, _MOVEMENTS_PATH])
async def test_get_projection_without_token_returns_401(client: AsyncClient, path: str) -> None:
    """401: глобус и карта перемещений без Bearer-токена отклоняются кодом auth.invalid_access_token."""
    response = await client.get(path)

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_get_movements_map_returns_routes_and_year_bounds(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: маршруты с годами и годы первой и последней поездки в camelCase — у городов id и координаты, без страны."""
    user_id = uuid4()
    fake_journey_repository.journeys = [
        make_journey(user_id=user_id, traveled_year=2022),
        make_journey(user_id=user_id, traveled_year=2018),
    ]
    fake_journey_repository.movement_connections_by_user_id[user_id] = [
        MovementConnection(
            origin=make_geo_point(city_id=MOSCOW_CITY_ID, country_code="RU", latitude=55.75, longitude=37.62),
            destination=make_geo_point(city_id=LONDON_CITY_ID, country_code="GB", latitude=51.5, longitude=-0.12),
            years=(2018, 2021),
        ),
    ]

    response = await client.get(
        _MOVEMENTS_PATH, headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["firstYear"] == 2018
    assert body["lastYear"] == 2022
    [connection] = body["connections"]
    assert set(connection) == {"origin", "destination", "years"}
    assert set(connection["origin"]) == {"cityId", "latitude", "longitude"}
    assert connection["origin"]["cityId"] == str(MOSCOW_CITY_ID)
    assert connection["destination"]["cityId"] == str(LONDON_CITY_ID)
    assert connection["years"] == [2018, 2021]


async def test_get_movements_map_passes_transport_from_query(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """Повторяющийся transportType доходит до запроса маршрутов; без параметра — без фильтра; окна лет в запросе нет."""
    user_id = uuid4()
    fake_journey_repository.journeys = [make_journey(user_id=user_id, traveled_year=2018)]
    headers = {"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"}

    filtered = await client.get(
        _MOVEMENTS_PATH,
        # Прежний параметр окна лет игнорируется: окно применяет фронт.
        params=[("transportType", "air"), ("transportType", "water"), ("yearFrom", "2019")],
        headers=headers,
    )
    unfiltered = await client.get(_MOVEMENTS_PATH, headers=headers)

    assert filtered.status_code == 200
    assert unfiltered.status_code == 200
    assert fake_journey_repository.movement_connection_queries == [
        MovementConnectionQuery(
            user_id=user_id, transport_types=frozenset({TransportTypeEnum.AIR, TransportTypeEnum.WATER})
        ),
        MovementConnectionQuery(user_id=user_id, transport_types=None),
    ]


async def test_get_movements_map_unknown_transport_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """422: неизвестный вид транспорта — ошибка формы запроса validation_error."""
    response = await client.get(
        _MOVEMENTS_PATH,
        params={"transportType": "rocket"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", _FEED_PATH),
        ("GET", _YEARS_PATH),
        ("GET", _DISTANCE_PATH),
        ("PUT", f"/v1/journeys/{uuid4()}/"),
        ("DELETE", f"/v1/journeys/{uuid4()}/"),
        ("POST", f"/v1/journeys/{uuid4()}/move/"),
    ],
)
async def test_journey_routes_without_token_return_401(client: AsyncClient, method: str, path: str) -> None:
    """401: лента, годы, расстояние, правка, удаление и перенос без Bearer-токена отклоняются."""
    response = await client.request(method, path)

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_list_journeys_returns_feed_page_in_camel_case_with_cursor(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: страница ленты — свежий год сверху, поля в camelCase, курсор ведёт на следующую страницу."""
    user_id = uuid4()
    newer = make_journey(user_id=user_id, traveled_year=2021, distance_km=10)
    older = make_journey(user_id=user_id, traveled_year=2019, distance_km=20)
    fake_journey_repository.journeys = [older, newer]
    headers = {"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"}

    first = await client.get(_FEED_PATH, params={"limit": 1}, headers=headers)
    second = await client.get(_FEED_PATH, params={"limit": 1, "cursor": first.json()["nextCursor"]}, headers=headers)

    assert first.status_code == 200
    assert first.json()["items"] == [
        {
            "journeyId": str(newer.journey_id),
            "origin": {
                "cityId": str(newer.origin.city_id),
                "countryCode": newer.origin.country_code,
                "latitude": newer.origin.latitude,
                "longitude": newer.origin.longitude,
            },
            "destination": {
                "cityId": str(newer.destination.city_id),
                "countryCode": newer.destination.country_code,
                "latitude": newer.destination.latitude,
                "longitude": newer.destination.longitude,
            },
            "transportType": "air",
            "traveledYear": 2021,
            "distanceKm": 10,
        }
    ]
    assert [item["journeyId"] for item in second.json()["items"]] == [str(older.journey_id)]
    assert second.json()["nextCursor"] is None


async def test_list_journeys_passes_year_and_transport_filters(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: yearFrom/yearTo и повторяемый transportType из query фильтруют ленту."""
    user_id = uuid4()
    matching = make_journey(user_id=user_id, traveled_year=2020, transport_type=TransportTypeEnum.WATER)
    fake_journey_repository.journeys = [
        matching,
        make_journey(user_id=user_id, traveled_year=2020, transport_type=TransportTypeEnum.LAND),
        make_journey(user_id=user_id, traveled_year=2022, transport_type=TransportTypeEnum.WATER),
    ]

    response = await client.get(
        _FEED_PATH,
        params=[("yearFrom", "2019"), ("yearTo", "2020"), ("transportType", "water"), ("transportType", "air")],
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"},
    )

    assert response.status_code == 200
    assert [item["journeyId"] for item in response.json()["items"]] == [str(matching.journey_id)]


@pytest.mark.parametrize(
    ("params", "expected_code"),
    [
        ({"yearFrom": 2021, "yearTo": 2020}, "journeys.invalid_year_range"),
        ({"cursor": "not-a-cursor"}, "invalid_cursor"),
    ],
)
async def test_list_journeys_bad_query_returns_400(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
    params: dict[str, Any],
    expected_code: str,
) -> None:
    """400: диапазон лет наоборот и битый курсор отдают свои коды, а не общий 422."""
    response = await client.get(
        _FEED_PATH,
        params=params,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == expected_code


async def test_get_journey_years_returns_years_ascending(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: годы поездок пользователя по возрастанию, без повторов."""
    user_id = uuid4()
    fake_journey_repository.journeys = [
        make_journey(user_id=user_id, traveled_year=2021),
        make_journey(user_id=user_id, traveled_year=2019),
        make_journey(user_id=user_id, traveled_year=2021),
    ]

    response = await client.get(_YEARS_PATH, headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"})

    assert response.status_code == 200
    assert response.json() == {"years": [2019, 2021]}


async def test_estimate_journey_distance_returns_great_circle_km(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """200: расстояние Москва → Лондон по id городов, координаты — из geo (~2500 км)."""
    response = await client.get(
        _DISTANCE_PATH,
        params=_ROUTE,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 200
    assert response.json()["distanceKm"] == pytest.approx(2500, abs=60)


@pytest.mark.parametrize(
    ("is_london_known", "params", "expected_code"),
    [
        (True, {**_ROUTE, "destinationCityId": str(MOSCOW_CITY_ID)}, "journeys.same_origin_destination"),
        (False, _ROUTE, "journeys.unknown_city"),
    ],
)
async def test_estimate_journey_distance_rejected_returns_400(
    client: AsyncClient,
    fake_cities_client: FakeCitiesClient,
    mint_access_token: Callable[..., str],
    is_london_known: bool,
    params: dict[str, str],
    expected_code: str,
) -> None:
    """400: тот же город или города нет в geo — коды как при сохранении поездки."""
    if not is_london_known:
        del fake_cities_client.locations[LONDON_CITY_ID]

    response = await client.get(
        _DISTANCE_PATH,
        params=params,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == expected_code


async def test_update_journey_returns_204_and_replaces_fields(
    client: AsyncClient,
    fake_journey_uow: FakeJourneyUnitOfWork,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """204: правка заменяет поля поездки владельца, страна и координаты городов — из geo; тело пустое, один commit."""
    user_id = uuid4()
    journey_entity = make_journey(
        user_id=user_id,
        origin=make_geo_point(city_id=uuid4(), country_code="FR", latitude=48.85, longitude=2.35),
        destination=make_geo_point(city_id=uuid4(), country_code="DE", latitude=52.52, longitude=13.4),
        transport_type=TransportTypeEnum.WATER,
        traveled_year=2018,
    )
    fake_journey_repository.journeys = [journey_entity]

    response = await client.put(
        f"/v1/journeys/{journey_entity.journey_id}/",
        json=_VALID_BODY,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"},
    )

    assert response.status_code == 204
    assert response.content == b""
    updated = fake_journey_repository.journeys[0]
    assert updated.origin.city_id == MOSCOW_CITY_ID
    assert updated.origin.country_code == "RU"
    assert updated.destination.city_id == LONDON_CITY_ID
    assert updated.destination.country_code == "GB"
    assert updated.destination.latitude == pytest.approx(51.5)
    assert updated.transport_type is TransportTypeEnum.AIR
    assert updated.traveled_year == 2020
    fake_journey_uow.commit_mock.assert_awaited_once()


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"destinationCityId": str(MOSCOW_CITY_ID)}, "journeys.same_origin_destination"),
        ({"traveledYear": _CURRENT_YEAR + 1}, "journeys.date_in_future"),
    ],
)
async def test_update_journey_rejected_by_request_rules_returns_400(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
    overrides: dict[str, Any],
    expected_code: str,
) -> None:
    """400: правка подчиняется тем же правилам схемы, что и создание; поездка не меняется."""
    user_id = uuid4()
    journey_entity = make_journey(user_id=user_id, traveled_year=2018)
    fake_journey_repository.journeys = [journey_entity]

    response = await client.put(
        f"/v1/journeys/{journey_entity.journey_id}/",
        json={**_VALID_BODY, **overrides},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == expected_code
    assert fake_journey_repository.journeys[0].traveled_year == 2018


async def test_update_journey_of_another_user_returns_404(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """404: чужая поездка выглядит как несуществующая — journeys.journey_not_found."""
    journey_entity = make_journey(user_id=uuid4())
    fake_journey_repository.journeys = [journey_entity]

    response = await client.put(
        f"/v1/journeys/{journey_entity.journey_id}/",
        json=_VALID_BODY,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "journeys.journey_not_found"


async def test_delete_journey_returns_204_and_soft_deletes(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """204: удаление помечает поездку удалённой, повторное удаление — 404."""
    user_id = uuid4()
    journey_entity = make_journey(user_id=user_id)
    fake_journey_repository.journeys = [journey_entity]
    headers = {"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"}

    first = await client.delete(f"/v1/journeys/{journey_entity.journey_id}/", headers=headers)
    second = await client.delete(f"/v1/journeys/{journey_entity.journey_id}/", headers=headers)

    assert first.status_code == 204
    assert fake_journey_repository.journeys[0].is_deleted
    assert second.status_code == 404
    assert second.json()["code"] == "journeys.journey_not_found"


async def test_move_journey_returns_200_with_neighbor_year(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: перенос к соседу из другого года отдаёт новый год поездки."""
    user_id = uuid4()
    neighbor_entity = make_journey(user_id=user_id, traveled_year=2018)
    moved_entity = make_journey(user_id=user_id, traveled_year=2020)
    fake_journey_repository.journeys = [neighbor_entity, moved_entity]

    response = await client.post(
        f"/v1/journeys/{moved_entity.journey_id}/move/",
        json={"neighborJourneyId": str(neighbor_entity.journey_id), "placement": "before"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"},
    )

    assert response.status_code == 200
    assert response.json() == {"traveledYear": 2018}
    assert moved_entity.traveled_year == 2018


async def test_move_journey_to_foreign_neighbor_returns_400(
    client: AsyncClient,
    fake_journey_repository: FakeJourneyRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """400: сосед чужой — journeys.invalid_move_target, поездка не двигается."""
    user_id = uuid4()
    moved_entity = make_journey(user_id=user_id, traveled_year=2020)
    foreign_entity = make_journey(user_id=uuid4(), traveled_year=2018)
    fake_journey_repository.journeys = [moved_entity, foreign_entity]

    response = await client.post(
        f"/v1/journeys/{moved_entity.journey_id}/move/",
        json={"neighborJourneyId": str(foreign_entity.journey_id), "placement": "after"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_id)}"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "journeys.invalid_move_target"
    assert moved_entity.traveled_year == 2020


async def test_move_journey_unknown_placement_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """422: placement не after/before — ошибка формы запроса validation_error."""
    response = await client.post(
        f"/v1/journeys/{uuid4()}/move/",
        json={"neighborJourneyId": str(uuid4()), "placement": "inside"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
