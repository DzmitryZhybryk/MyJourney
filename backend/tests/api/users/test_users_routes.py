"""
api-тесты роута ``GET /v1/users/me/`` на ASGI-приложении.

Реальный ``UserService`` поверх фейк-UoW, реальный декод Bearer-токена (подписан
settings-секретом через ``mint_access_token``). Пиннят camelCase-контракт ответа
(``displayName``), 401 без токена, 404 для неизвестного id и 410 для soft-deleted.
"""

import datetime as dt
from collections.abc import Callable
from uuid import uuid4

from httpx import AsyncClient

from tests.builders import make_user_entity
from tests.fakes import FakeUserRepository

_ME_PATH = "/v1/users/me/"


async def test_get_current_user_returns_camelcase_profile(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: профиль текущего пользователя, ключ displayName в camelCase."""
    user_entity = make_user_entity(display_name="Alice D.")
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.get(
        _ME_PATH,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 200
    assert response.json() == {"displayName": "Alice D."}


async def test_get_current_user_without_token_returns_401(client: AsyncClient) -> None:
    """401: запрос без Bearer-токена отклоняется с кодом auth.invalid_access_token."""
    response = await client.get(_ME_PATH)

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_get_current_user_unknown_id_returns_404(
    client: AsyncClient,
    mint_access_token: Callable[..., str],
) -> None:
    """404: валидный токен, но пользователя нет в хранилище → users.user_not_found."""
    response = await client.get(_ME_PATH, headers={"Authorization": f"Bearer {mint_access_token(user_id=uuid4())}"})

    assert response.status_code == 404
    assert response.json()["code"] == "users.user_not_found"


async def test_get_current_user_soft_deleted_returns_410(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """410: пользователь soft-deleted → users.user_deleted."""
    user_entity = make_user_entity(deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC))
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.get(
        _ME_PATH,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 410
    assert response.json()["code"] == "users.user_deleted"
