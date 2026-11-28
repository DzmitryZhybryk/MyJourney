import datetime as dt
from uuid import UUID

from procrastinate import JobContext

from app.backoffice.application.ports.account_repository import AccountListItem
from app.backoffice.infra.repositories import AccountRepository
from app.backoffice.infra.tasks import apply_account_changed, apply_profile_changed
from app.shared.enums import SortDirectionEnum
from app.shared.events import AccountChangedEvent, ProfileChangedEvent
from app.shared.pagination.offset import OffsetPageQuery
from tests.builders import make_account_filters


async def test_apply_tasks_write_both_event_snapshots_into_one_row(
    job_context: JobContext,
    account_repository: AccountRepository,
) -> None:
    """Таски учётной записи и профиля переносят каждое поле события в общую строку аккаунта."""
    user_id = UUID(int=1)
    account_changed_event = AccountChangedEvent(
        user_id=user_id,
        email="neo@example.com",
        username="neo",
        role="admin",
        plan="premium",
        email_verified_at=dt.datetime(2026, 1, 2, tzinfo=dt.UTC),
        registered_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        deleted_at=dt.datetime(2026, 1, 3, tzinfo=dt.UTC),
        version=2,
    )
    profile_changed_event = ProfileChangedEvent(
        user_id=user_id,
        display_name="Neo",
        marketing_emails_consent=True,
        terms_accepted_at=dt.datetime(2026, 1, 1, 12, tzinfo=dt.UTC),
        version=1,
    )

    await apply_account_changed(job_context, event=account_changed_event.model_dump(mode="json"))
    await apply_profile_changed(job_context, event=profile_changed_event.model_dump(mode="json"))
    page = await account_repository.find_accounts_page(
        page=OffsetPageQuery(page=1, limit=20),
        filters=make_account_filters(include_deleted=True),
        sort_direction=SortDirectionEnum.DESC,
    )

    assert page.items == (
        AccountListItem(
            user_id=user_id,
            email="neo@example.com",
            username="neo",
            role="admin",
            plan="premium",
            email_verified_at=account_changed_event.email_verified_at,
            registered_at=account_changed_event.registered_at,
            deleted_at=account_changed_event.deleted_at,
            display_name="Neo",
            marketing_emails_consent=True,
            terms_accepted_at=profile_changed_event.terms_accepted_at,
        ),
    )
