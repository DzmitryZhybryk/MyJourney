import datetime as dt
from typing import Annotated
from uuid import UUID

from pydantic import ConfigDict, Field

from app.shared.enums import SortDirectionEnum
from app.shared.pagination.offset.schemas import OffsetPageFields, OffsetPaginationFields
from app.shared.schemas.base import CamelModel


class AdminAccountsListRequest(OffsetPaginationFields):
    """
    Страница списка аккаунтов, её фильтр и направление сортировки (query-параметры).

    ``email`` и ``displayName`` — подстрока без учёта регистра, ``role`` — точное значение; без параметра —
    без фильтра. Удалённые скрыты, пока не передан ``includeDeleted=true``. Сортировка — по дате регистрации,
    по умолчанию от новых к старым.
    """

    email: Annotated[str | None, Field(min_length=1, max_length=254)] = None
    display_name: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    role: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    marketing_emails_consent: bool | None = None
    include_deleted: bool = False
    sort_direction: SortDirectionEnum = SortDirectionEnum.DESC


class AccountListEntry(CamelModel):
    """Аккаунт в списке; пустое поле — данные учётной записи или профиля ещё не дошли до списка."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    email: str | None
    username: str | None
    role: str | None
    plan: str | None
    email_verified_at: dt.datetime | None
    registered_at: dt.datetime | None
    deleted_at: dt.datetime | None
    display_name: str | None
    marketing_emails_consent: bool | None
    terms_accepted_at: dt.datetime | None


class AdminAccountsListResponse(OffsetPageFields[AccountListEntry]):
    """Страница списка аккаунтов и число всех аккаунтов под фильтром."""
