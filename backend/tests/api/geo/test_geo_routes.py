"""
api-тесты роутов geo на ASGI-приложении: ``GET /v1/geo/cities/search/`` и
``POST /v1/geo/cities/resolve/``.

Реальная проводка ``city_service`` поверх фейк-репозитория, реальный декод Bearer-токена
(подписан settings-секретом через ``mint_access_token``). Пиннят camelCase-контракт ответа,
401 без токена и 422 на невалидный ввод.
"""

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.builders import make_city
from tests.fakes import FakeCityRepository

_SEARCH_PATH = "/v1/geo/cities/search/"
_RESOLVE_PATH = "/v1/geo/cities/resolve/"


async def test_search_cities_returns_camelcase_candidates(
    client: AsyncClient,
    fake_city_repository: FakeCityRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: имена резолвятся под язык, ответ camelCase (cityId/countryCode), порядок по населению."""
    moscow = make_city(en="Moscow", ru="Москва", country_code="RU", population=10_000_000)
    mostar = make_city(en="Mostar", ru=None, country_code="BA", population=100_000)
    fake_city_repository.cities.extend([mostar, moscow])

    response = await client.get(
        _SEARCH_PATH,
        params={"searchText": "Mos", "language": "ru", "limit": 10},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["name"] for item in items] == ["Москва", "Mostar"]
    first = items[0]
    assert UUID(first["cityId"]) == moscow.city_id
    assert first["countryCode"] == "RU"
    assert "city_id" not in first
    assert "country_code" not in first


async def test_search_cities_query_with_surrounding_spaces_is_trimmed(
    client: AsyncClient,
    fake_city_repository: FakeCityRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: пробелы по краям searchText срезаются, префикс «Mos» находит Moscow."""
    fake_city_repository.cities.append(make_city(en="Moscow", ru="Москва", country_code="RU"))

    response = await client.get(
        _SEARCH_PATH,
        params={"searchText": "  Mos  ", "language": "en"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["Moscow"]


async def test_search_cities_without_token_returns_401(client: AsyncClient) -> None:
    """401: запрос без Bearer-токена отклоняется с кодом auth.invalid_access_token."""
    response = await client.get(_SEARCH_PATH, params={"searchText": "Mos", "language": "en"})

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_search_cities_missing_language_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """422: обязательный query-параметр language отсутствует → validation_error."""
    response = await client.get(
        _SEARCH_PATH,
        params={"searchText": "Mos"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.parametrize("search_text", ["M", "  M  ", "   "])
async def test_search_cities_too_short_query_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
    search_text: str,
) -> None:
    """422: поиск короче двух символов (в т.ч. после обрезки пробелов) отклоняется."""
    response = await client.get(
        _SEARCH_PATH,
        params={"searchText": search_text, "language": "en"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422


async def test_resolve_cities_returns_names_and_omits_unknown(
    client: AsyncClient,
    fake_city_repository: FakeCityRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: названия на языке запроса в camelCase, неизвестный id в ответ не попадает."""
    moscow = make_city(en="Moscow", ru="Москва")
    fake_city_repository.cities.append(moscow)

    response = await client.post(
        _RESOLVE_PATH,
        json={"cityIds": [str(moscow.city_id), str(uuid4())], "language": "ru"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 200
    assert response.json() == {"items": [{"cityId": str(moscow.city_id), "name": "Москва"}]}


async def test_resolve_cities_without_token_returns_401(client: AsyncClient) -> None:
    """401: запрос названий без Bearer-токена отклоняется."""
    response = await client.post(_RESOLVE_PATH, json={"cityIds": [str(uuid4())], "language": "en"})

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_resolve_cities_empty_list_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """422: пустой список id — нечего спрашивать."""
    response = await client.post(
        _RESOLVE_PATH,
        json={"cityIds": [], "language": "en"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422


async def test_resolve_cities_more_than_1000_ids_returns_422(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """422: больше 1000 id за запрос — фронт обязан резать список на части."""
    response = await client.post(
        _RESOLVE_PATH,
        json={"cityIds": [str(uuid4()) for _ in range(1001)], "language": "en"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 422


async def test_resolve_cities_accepts_exactly_1000_ids(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """200: ровно 1000 id — это ещё в пределах лимита, по которому фронт режет список."""
    response = await client.post(
        _RESOLVE_PATH,
        json={"cityIds": [str(uuid4()) for _ in range(1000)], "language": "en"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"},
    )

    assert response.status_code == 200
