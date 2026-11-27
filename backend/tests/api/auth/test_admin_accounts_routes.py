"""
api-тесты админской ручки учётных записей по списку id.

Токены выпускает настоящий ``TokenIssuer`` (``issue_access_token``): право администратора приходит из
карты ролей, а не задаётся руками. Репозиторий — фейк за UoW.
"""

import datetime as dt
from collections.abc import Callable
from typing import Final
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.auth.domain.entities import UserCredentialsEntity
from app.auth.domain.enums import UserRoleEnum
from tests.builders import make_user_credentials
from tests.fakes import FakeUserCredentialsRepository

_PATH: Final[str] = "/v1/admin/auth/accounts/"
_OPTIONS_PATH: Final[str] = "/v1/admin/auth/account-options/"


async def test_find_accounts_by_ids_admin_token_returns_email_and_deleted_flag(
    client: AsyncClient,
    fake_user_credentials_repository: FakeUserCredentialsRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """Админ получает email и пометку удаления по каждому найденному id; неизвестный id в ответ не попадает."""
    active_entity = make_user_credentials(email="neo@example.com", username="neo")
    deleted_entity = make_user_credentials(
        email="smith@example.com",
        username="smith",
        deleted_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )
    for user_credentials_entity in (active_entity, deleted_entity):
        await fake_user_credentials_repository.insert_user_credentials(user_credentials_entity)
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.get(
        _PATH,
        params={"ids": [str(active_entity.user_id), str(deleted_entity.user_id), str(uuid4())]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    accounts = response.json()["accounts"]
    assert sorted(accounts, key=lambda account: account["email"]) == [
        {"id": str(active_entity.user_id), "email": "neo@example.com", "isDeleted": False},
        {"id": str(deleted_entity.user_id), "email": "smith@example.com", "isDeleted": True},
    ]


async def test_find_accounts_by_ids_user_token_returns_permission_required(
    client: AsyncClient,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """403 ``permission_required`` у обычного пользователя."""
    token = issue_access_token(make_user_credentials())

    response = await client.get(_PATH, params={"ids": [str(uuid4())]}, headers={"Authorization": f"Bearer {token}"})

    assert (response.status_code, response.json()["code"]) == (403, "permission_required")


async def test_find_accounts_by_ids_without_token_returns_unauthenticated(client: AsyncClient) -> None:
    """401 без Bearer."""
    response = await client.get(_PATH, params={"ids": [str(uuid4())]})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "ids",
    [
        pytest.param([], id="missing"),
        pytest.param([str(uuid4()) for _ in range(101)], id="over-limit"),
        pytest.param(["not-a-uuid"], id="malformed"),
    ],
)
async def test_find_accounts_by_ids_invalid_ids_returns_validation_error(
    client: AsyncClient,
    issue_access_token: Callable[[UserCredentialsEntity], str],
    ids: list[str],
) -> None:
    """422 без id, больше 100 id или на id не в формате UUID."""
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.get(_PATH, params={"ids": ids}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422


async def test_get_account_options_admin_token_returns_roles_and_plans(
    client: AsyncClient,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """Админ получает все роли и тарифы значениями enum'ов в порядке объявления."""
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.get(_OPTIONS_PATH, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"roles": ["user", "admin"], "plans": ["free", "premium"]}


async def test_get_account_options_user_token_returns_permission_required(
    client: AsyncClient,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """403 ``permission_required`` у обычного пользователя."""
    token = issue_access_token(make_user_credentials())

    response = await client.get(_OPTIONS_PATH, headers={"Authorization": f"Bearer {token}"})

    assert (response.status_code, response.json()["code"]) == (403, "permission_required")


async def test_get_account_options_without_token_returns_unauthenticated(client: AsyncClient) -> None:
    """401 без Bearer."""
    response = await client.get(_OPTIONS_PATH)

    assert response.status_code == 401
