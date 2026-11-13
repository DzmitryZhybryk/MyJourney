"""
api-тесты роутов ``GET`` и ``PATCH /v1/users/me/`` на ASGI-приложении.

Реальный ``UserService`` поверх фейк-UoW, реальный декод Bearer-токена (подписан
settings-секретом через ``mint_access_token``). Пиннят camelCase-контракт ответа,
401 без токена, 404 для неизвестного id, 410 для soft-deleted и разбор тела PATCH:
отсутствующее поле не меняется, явный ``null`` и неверное имя — 422.
"""

import datetime as dt
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.builders import make_user_entity
from tests.fakes import FakeUserRepository

_ME_PATH = "/v1/users/me/"


async def test_get_current_user_returns_camelcase_profile(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: профиль текущего пользователя, ключи в camelCase."""
    user_entity = make_user_entity(display_name="Alice D.", marketing_emails_consent=True)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.get(
        _ME_PATH,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 200
    assert response.json() == {"displayName": "Alice D.", "marketingEmailsConsent": True}


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


async def test_update_current_user_trims_name_and_returns_profile(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: имя обрезается по краям, ответ — весь профиль в camelCase."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.patch(
        _ME_PATH,
        json={"displayName": "  Alice D.  "},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 200
    assert response.json() == {"displayName": "Alice D.", "marketingEmailsConsent": True}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"marketingEmailsConsent": False}, {"displayName": "alice", "marketingEmailsConsent": False}),
        ({}, {"displayName": "alice", "marketingEmailsConsent": True}),
    ],
    ids=["only-consent", "empty-body"],
)
async def test_update_current_user_absent_field_is_unchanged(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
    body: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """200: поле, которого нет в теле, сохраняет прежнее значение."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.patch(
        _ME_PATH,
        json=body,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize(
    "body",
    [
        {"displayName": ""},
        {"displayName": "   "},
        {"displayName": "a" * 51},
        {"displayName": "a\u0000b"},
        {"displayName": "a\nb"},
        {"displayName": "a\u0085b"},
        {"displayName": None},
        {"marketingEmailsConsent": None},
    ],
    ids=["empty", "whitespace-only", "51-chars", "nul-char", "newline", "c1-control", "null-name", "null-consent"],
)
async def test_update_current_user_invalid_body_returns_422_and_changes_nothing(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
    body: dict[str, Any],
) -> None:
    """422 validation_error: неверное имя или явный null; профиль не тронут."""
    user_entity = make_user_entity(display_name="alice", marketing_emails_consent=True)
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.patch(
        _ME_PATH,
        json=body,
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert fake_user_repository.updated_user_ids == []


async def test_update_current_user_accepts_50_char_name(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """200: имя ровно на границе — 50 символов."""
    user_entity = make_user_entity()
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.patch(
        _ME_PATH,
        json={"displayName": "a" * 50},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 200
    assert response.json()["displayName"] == "a" * 50


async def test_update_current_user_without_token_returns_401(client: AsyncClient) -> None:
    """401: PATCH без Bearer-токена отклоняется с кодом auth.invalid_access_token."""
    response = await client.patch(_ME_PATH, json={"displayName": "Alice"})

    assert response.status_code == 401
    assert response.json()["code"] == "auth.invalid_access_token"


async def test_update_current_user_soft_deleted_returns_410(
    client: AsyncClient,
    fake_user_repository: FakeUserRepository,
    mint_access_token: Callable[..., str],
) -> None:
    """410: правка профиля soft-deleted пользователя → users.user_deleted."""
    user_entity = make_user_entity(deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC))
    fake_user_repository.by_user_id[user_entity.user_id] = user_entity

    response = await client.patch(
        _ME_PATH,
        json={"displayName": "Alice"},
        headers={"Authorization": f"Bearer {mint_access_token(user_id=user_entity.user_id)}"},
    )

    assert response.status_code == 410
    assert response.json()["code"] == "users.user_deleted"
