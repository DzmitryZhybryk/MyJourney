from dataclasses import dataclass

from app.backoffice.application.ports.account_repository import AccountListItem
from app.shared.pagination.offset import OffsetPage

__all__ = ["ListAccountsResult"]


@dataclass(frozen=True, slots=True)
class ListAccountsResult(OffsetPage[AccountListItem]):
    """Страница списка аккаунтов и число всех аккаунтов под фильтром."""
