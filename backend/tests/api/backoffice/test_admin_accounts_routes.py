"""
api-тесты админского списка аккаунтов.

Токены выпускает настоящий ``TokenIssuer``: право приходит из карты ролей. Хранилище — фейк за UoW: тест
проверяет, во что ручка превращает query-параметры и как отдаёт страницу; сам SQL — в integration.
"""

import datetime as dt
from collections.abc import Callable
from typing import Final
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.auth.domain.entities import UserCredentialsEntity
from app.auth.domain.enums import UserRoleEnum
from app.backoffice.application.ports.account_repository import AccountListItem
from app.shared.enums import SortDirectionEnum
from app.shared.pagination.offset import OffsetPage, OffsetPageQuery
from tests.builders import make_account_filters, make_user_credentials
from tests.fakes import AccountsPageQuery, FakeAccountRepository

_PATH: Final[str] = "/v1/admin/backoffice/accounts/"


async def test_list_accounts_admin_token_returns_page_in_camel_case_with_nulls(
    client: AsyncClient,
    fake_account_repository: FakeAccountRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """Админ получает страницу и total; поля в camelCase, недошедшие части строки — null."""
    fake_account_repository.accounts_page = OffsetPage(
        items=(
            AccountListItem(
                user_id=UUID(int=1),
                email="neo@example.com",
                username="neo",
                role="admin",
                plan="free",
                email_verified_at=None,
                registered_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
                deleted_at=None,
                display_name=None,
                marketing_emails_consent=None,
                terms_accepted_at=None,
            ),
        ),
        total=21,
    )
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.get(_PATH, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "userId": str(UUID(int=1)),
                "email": "neo@example.com",
                "username": "neo",
                "role": "admin",
                "plan": "free",
                "emailVerifiedAt": None,
                "registeredAt": "2026-01-01T00:00:00Z",
                "deletedAt": None,
                "displayName": None,
                "marketingEmailsConsent": None,
                "termsAcceptedAt": None,
            },
        ],
        "total": 21,
    }


async def test_list_accounts_without_params_asks_first_page_newest_first_without_deleted(
    client: AsyncClient,
    fake_account_repository: FakeAccountRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """Без параметров — первая страница из 20, без фильтров, удалённые скрыты, сначала новые."""
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    await client.get(_PATH, headers={"Authorization": f"Bearer {token}"})

    assert fake_account_repository.page_queries == [
        AccountsPageQuery(
            page=OffsetPageQuery(page=1, limit=20),
            filters=make_account_filters(),
            sort_direction=SortDirectionEnum.DESC,
        ),
    ]


async def test_list_accounts_maps_every_query_param_into_the_query(
    client: AsyncClient,
    fake_account_repository: FakeAccountRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """Каждый query-параметр доходит до хранилища в своё поле."""
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    await client.get(
        _PATH,
        params={
            "page": 3,
            "limit": 50,
            "email": "neo",
            "displayName": "Ne",
            "role": "admin",
            "marketingEmailsConsent": "false",
            "includeDeleted": "true",
            "sortDirection": "asc",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert fake_account_repository.page_queries == [
        AccountsPageQuery(
            page=OffsetPageQuery(page=3, limit=50),
            filters=make_account_filters(
                email_contains="neo",
                display_name_contains="Ne",
                role="admin",
                marketing_emails_consent=False,
                include_deleted=True,
            ),
            sort_direction=SortDirectionEnum.ASC,
        ),
    ]


async def test_list_accounts_user_token_returns_permission_required(
    client: AsyncClient,
    issue_access_token: Callable[[UserCredentialsEntity], str],
) -> None:
    """403 ``permission_required`` у обычного пользователя."""
    token = issue_access_token(make_user_credentials())

    response = await client.get(_PATH, headers={"Authorization": f"Bearer {token}"})

    assert (response.status_code, response.json()["code"]) == (403, "permission_required")


async def test_list_accounts_without_token_returns_unauthenticated(client: AsyncClient) -> None:
    """401 без Bearer."""
    response = await client.get(_PATH)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 0}, id="page-zero"),
        pytest.param({"page": 10_001}, id="page-over-limit"),
        pytest.param({"limit": 101}, id="limit-over-limit"),
        pytest.param({"email": ""}, id="empty-email"),
        pytest.param({"email": "a" * 255}, id="email-too-long"),
        pytest.param({"displayName": "a" * 51}, id="display-name-too-long"),
        pytest.param({"role": ""}, id="empty-role"),
        pytest.param({"sortDirection": "sideways"}, id="unknown-direction"),
    ],
)
async def test_list_accounts_invalid_params_returns_validation_error(
    client: AsyncClient,
    fake_account_repository: FakeAccountRepository,
    issue_access_token: Callable[[UserCredentialsEntity], str],
    params: dict[str, str | int],
) -> None:
    """422 на параметр вне границ; до хранилища запрос не доходит."""
    token = issue_access_token(make_user_credentials(role=UserRoleEnum.ADMIN))

    response = await client.get(_PATH, params=params, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422
    assert fake_account_repository.page_queries == []
