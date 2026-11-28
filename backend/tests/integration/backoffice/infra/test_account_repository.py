import datetime as dt
from typing import Final
from uuid import UUID

import pytest

from app.backoffice.application.ports.account_repository import AccountListItem
from app.backoffice.infra.repositories import AccountRepository
from app.shared.enums import SortDirectionEnum
from app.shared.pagination.offset import OffsetPageQuery
from tests.builders import make_account_auth_part, make_account_filters, make_account_profile_part

_FIRST_PAGE: Final[OffsetPageQuery] = OffsetPageQuery(page=1, limit=20)
_DELETED_AT: Final[dt.datetime] = dt.datetime(2026, 3, 1, tzinfo=dt.UTC)


async def test_upsert_auth_part_into_empty_table_leaves_profile_columns_empty(
    account_repository: AccountRepository,
) -> None:
    """Первый снимок учётной записи создаёт строку: колонки учётной записи заполнены, профиля — пусты."""
    user_id = UUID(int=1)
    auth_part = make_account_auth_part(email="neo@example.com", username="neo", role="admin", plan="premium")

    await account_repository.upsert_account_auth_part(user_id=user_id, auth_part=auth_part)
    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert page.items == (
        AccountListItem(
            user_id=user_id,
            email="neo@example.com",
            username="neo",
            role="admin",
            plan="premium",
            email_verified_at=None,
            registered_at=auth_part.registered_at,
            deleted_at=None,
            display_name=None,
            marketing_emails_consent=None,
            terms_accepted_at=None,
        ),
    )
    assert page.total == 1


async def test_upsert_parts_in_reverse_order_fill_one_row(account_repository: AccountRepository) -> None:
    """Профиль раньше учётной записи: обе части оказываются в одной строке."""
    user_id = UUID(int=1)
    profile_part = make_account_profile_part(display_name="Neo", marketing_emails_consent=True)

    await account_repository.upsert_account_profile_part(user_id=user_id, profile_part=profile_part)
    await account_repository.upsert_account_auth_part(user_id=user_id, auth_part=make_account_auth_part())
    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert len(page.items) == 1
    assert page.items[0].email == "user@example.com"
    assert page.items[0].display_name == "Neo"
    assert page.items[0].marketing_emails_consent is True
    assert page.items[0].terms_accepted_at == profile_part.terms_accepted_at


async def test_upsert_auth_part_with_newer_version_overwrites(account_repository: AccountRepository) -> None:
    """Снимок учётной записи новее записанного переписывает её колонки."""
    user_id = UUID(int=1)
    verified_at = dt.datetime(2026, 2, 1, tzinfo=dt.UTC)
    await account_repository.upsert_account_auth_part(user_id=user_id, auth_part=make_account_auth_part(version=1))

    await account_repository.upsert_account_auth_part(
        user_id=user_id,
        auth_part=make_account_auth_part(email_verified_at=verified_at, version=2),
    )
    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert page.items[0].email_verified_at == verified_at


@pytest.mark.parametrize("late_version", [1, 2], ids=["older", "repeated"])
async def test_upsert_auth_part_not_newer_than_stored_is_ignored(
    account_repository: AccountRepository,
    late_version: int,
) -> None:
    """Опоздавший или повторный снимок учётной записи строку не меняет."""
    user_id = UUID(int=1)
    await account_repository.upsert_account_auth_part(
        user_id=user_id,
        auth_part=make_account_auth_part(email="current@example.com", version=2),
    )

    await account_repository.upsert_account_auth_part(
        user_id=user_id,
        auth_part=make_account_auth_part(email="late@example.com", version=late_version),
    )
    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert page.items[0].email == "current@example.com"


@pytest.mark.parametrize("late_version", [1, 2], ids=["older", "repeated"])
async def test_upsert_profile_part_not_newer_than_stored_is_ignored(
    account_repository: AccountRepository,
    late_version: int,
) -> None:
    """Опоздавший или повторный снимок профиля строку не меняет; новее — переписывает."""
    user_id = UUID(int=1)
    await account_repository.upsert_account_auth_part(user_id=user_id, auth_part=make_account_auth_part())
    await account_repository.upsert_account_profile_part(
        user_id=user_id,
        profile_part=make_account_profile_part(display_name="Current", version=2),
    )

    await account_repository.upsert_account_profile_part(
        user_id=user_id,
        profile_part=make_account_profile_part(display_name="Late", version=late_version),
    )
    stale_page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )
    await account_repository.upsert_account_profile_part(
        user_id=user_id,
        profile_part=make_account_profile_part(display_name="Newer", version=3),
    )
    newer_page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert stale_page.items[0].display_name == "Current"
    assert newer_page.items[0].display_name == "Newer"


async def test_upsert_auth_part_does_not_touch_profile_columns(account_repository: AccountRepository) -> None:
    """Новый снимок учётной записи не стирает колонки профиля той же строки."""
    user_id = UUID(int=1)
    await account_repository.upsert_account_auth_part(user_id=user_id, auth_part=make_account_auth_part(version=1))
    await account_repository.upsert_account_profile_part(
        user_id=user_id,
        profile_part=make_account_profile_part(display_name="Neo"),
    )

    await account_repository.upsert_account_auth_part(user_id=user_id, auth_part=make_account_auth_part(version=2))
    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert page.items[0].display_name == "Neo"


async def test_find_accounts_page_hides_deleted_unless_asked(account_repository: AccountRepository) -> None:
    """Удалённый аккаунт скрыт по умолчанию и виден с ``include_deleted``."""
    await account_repository.upsert_account_auth_part(user_id=UUID(int=1), auth_part=make_account_auth_part())
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=2),
        auth_part=make_account_auth_part(deleted_at=_DELETED_AT),
    )

    default_page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )
    with_deleted_page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(include_deleted=True),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert [item.user_id for item in default_page.items] == [UUID(int=1)]
    assert default_page.total == 1
    assert {item.user_id for item in with_deleted_page.items} == {UUID(int=1), UUID(int=2)}
    assert with_deleted_page.total == 2


async def test_find_accounts_page_email_filter_is_case_insensitive_substring(
    account_repository: AccountRepository,
) -> None:
    """Фильтр по email — подстрока без учёта регистра."""
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=1),
        auth_part=make_account_auth_part(email="Neo.Anderson@matrix.io"),
    )
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=2),
        auth_part=make_account_auth_part(email="trinity@matrix.io"),
    )

    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(email_contains="anDERSON"),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert [item.user_id for item in page.items] == [UUID(int=1)]
    assert page.total == 1


@pytest.mark.parametrize(
    ("needle", "expected_user_id"),
    [("_", UUID(int=1)), ("%", UUID(int=2))],
    ids=["underscore", "percent"],
)
async def test_find_accounts_page_substring_treats_like_wildcards_literally(
    account_repository: AccountRepository,
    needle: str,
    expected_user_id: UUID,
) -> None:
    """``_`` и ``%`` в фильтре ищутся как символы, а не как шаблоны LIKE."""
    await account_repository.upsert_account_profile_part(
        user_id=UUID(int=1),
        profile_part=make_account_profile_part(display_name="neo_one"),
    )
    await account_repository.upsert_account_profile_part(
        user_id=UUID(int=2),
        profile_part=make_account_profile_part(display_name="100% neo"),
    )
    await account_repository.upsert_account_profile_part(
        user_id=UUID(int=3),
        profile_part=make_account_profile_part(display_name="plain"),
    )

    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(display_name_contains=needle),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert [item.user_id for item in page.items] == [expected_user_id]


async def test_find_accounts_page_role_filter_is_exact(account_repository: AccountRepository) -> None:
    """Фильтр по роли — точное совпадение строки."""
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=1), auth_part=make_account_auth_part(role="admin")
    )
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=2), auth_part=make_account_auth_part(role="user")
    )

    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(role="admin"),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert [item.user_id for item in page.items] == [UUID(int=1)]


@pytest.mark.parametrize(("consent", "expected_user_id"), [(True, UUID(int=1)), (False, UUID(int=2))])
async def test_find_accounts_page_consent_filter_skips_rows_without_profile(
    account_repository: AccountRepository,
    consent: bool,
    expected_user_id: UUID,
) -> None:
    """Фильтр по согласию отбирает строки с этим значением; строка без профиля не попадает ни под одно."""
    await account_repository.upsert_account_profile_part(
        user_id=UUID(int=1),
        profile_part=make_account_profile_part(marketing_emails_consent=True),
    )
    await account_repository.upsert_account_profile_part(
        user_id=UUID(int=2),
        profile_part=make_account_profile_part(marketing_emails_consent=False),
    )
    await account_repository.upsert_account_auth_part(user_id=UUID(int=3), auth_part=make_account_auth_part())

    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(marketing_emails_consent=consent),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert [item.user_id for item in page.items] == [expected_user_id]


async def test_find_accounts_page_combines_filters_with_and(account_repository: AccountRepository) -> None:
    """Несколько фильтров сужают выдачу вместе: строка должна пройти каждый."""
    for user_id, role, display_name in [
        (UUID(int=1), "admin", "Neo"),
        (UUID(int=2), "admin", "Trinity"),
        (UUID(int=3), "user", "Neo"),
    ]:
        await account_repository.upsert_account_auth_part(user_id=user_id, auth_part=make_account_auth_part(role=role))
        await account_repository.upsert_account_profile_part(
            user_id=user_id,
            profile_part=make_account_profile_part(display_name=display_name),
        )

    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(role="admin", display_name_contains="neo"),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert [item.user_id for item in page.items] == [UUID(int=1)]
    assert page.total == 1


@pytest.mark.parametrize(
    ("sort_direction", "expected_order"),
    [
        (SortDirectionEnum.DESC, [UUID(int=3), UUID(int=2), UUID(int=1), UUID(int=4)]),
        (SortDirectionEnum.ASC, [UUID(int=1), UUID(int=2), UUID(int=3), UUID(int=4)]),
    ],
    ids=["desc", "asc"],
)
async def test_find_accounts_page_orders_by_registration_with_unregistered_last(
    account_repository: AccountRepository,
    sort_direction: SortDirectionEnum,
    expected_order: list[UUID],
) -> None:
    """Порядок — по дате регистрации в заданную сторону, одна дата — по ``user_id`` туда же, строка без даты в конце."""
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=1),
        auth_part=make_account_auth_part(registered_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC)),
    )
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=2),
        auth_part=make_account_auth_part(registered_at=dt.datetime(2026, 1, 2, tzinfo=dt.UTC)),
    )
    await account_repository.upsert_account_auth_part(
        user_id=UUID(int=3),
        auth_part=make_account_auth_part(registered_at=dt.datetime(2026, 1, 2, tzinfo=dt.UTC)),
    )
    await account_repository.upsert_account_profile_part(user_id=UUID(int=4), profile_part=make_account_profile_part())

    page = await account_repository.find_accounts_page(
        page=_FIRST_PAGE,
        filters=make_account_filters(),
        sort_direction=sort_direction,
    )

    assert [item.user_id for item in page.items] == expected_order


@pytest.mark.parametrize(
    ("page_number", "expected_user_ids"),
    [(1, [UUID(int=5), UUID(int=4)]), (3, [UUID(int=1)]), (4, [])],
    ids=["first", "last-partial", "past-the-end"],
)
async def test_find_accounts_page_slices_by_page_and_counts_all_matches(
    account_repository: AccountRepository,
    page_number: int,
    expected_user_ids: list[UUID],
) -> None:
    """Страница отдаёт свой срез, ``total`` — все строки под фильтром, и за концом списка тоже."""
    for day in range(1, 6):
        await account_repository.upsert_account_auth_part(
            user_id=UUID(int=day),
            auth_part=make_account_auth_part(registered_at=dt.datetime(2026, 1, day, tzinfo=dt.UTC)),
        )

    page = await account_repository.find_accounts_page(
        page=OffsetPageQuery(page=page_number, limit=2),
        filters=make_account_filters(),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert [item.user_id for item in page.items] == expected_user_ids
    assert page.total == 5
