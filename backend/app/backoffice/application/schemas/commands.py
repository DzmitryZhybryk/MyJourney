from dataclasses import dataclass

from app.backoffice.application.ports.account_repository import AccountAuthPart, AccountFilters, AccountProfilePart
from app.shared.enums import SortDirectionEnum
from app.shared.pagination.offset import OffsetPageQuery

__all__ = ["ApplyAccountChangedCommand", "ApplyProfileChangedCommand", "ListAccountsCommand"]


@dataclass(frozen=True, slots=True)
class ApplyAccountChangedCommand:
    """Новый снимок учётной записи для строки аккаунта."""

    auth_part: AccountAuthPart


@dataclass(frozen=True, slots=True)
class ApplyProfileChangedCommand:
    """Новый снимок профиля для строки аккаунта."""

    profile_part: AccountProfilePart


@dataclass(frozen=True, slots=True)
class ListAccountsCommand:
    """Какую страницу списка аккаунтов отдать, с каким фильтром и в каком направлении сортировки."""

    page: OffsetPageQuery
    filters: AccountFilters
    sort_direction: SortDirectionEnum
