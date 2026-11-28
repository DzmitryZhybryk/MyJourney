import datetime as dt
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.shared.enums import SortDirectionEnum
from app.shared.pagination.offset import OffsetPage, OffsetPageQuery

__all__ = ["AccountAuthPart", "AccountFilters", "AccountListItem", "AccountProfilePart", "AccountRepositoryPort"]


@dataclass(frozen=True, slots=True)
class AccountAuthPart:
    """Колонки строки аккаунта из учётной записи и версия снимка, из которого они взяты."""

    email: str
    username: str
    role: str
    plan: str
    email_verified_at: dt.datetime | None
    registered_at: dt.datetime
    deleted_at: dt.datetime | None
    version: int


@dataclass(frozen=True, slots=True)
class AccountProfilePart:
    """Колонки строки аккаунта из профиля и версия снимка, из которого они взяты."""

    display_name: str
    marketing_emails_consent: bool
    terms_accepted_at: dt.datetime
    version: int


@dataclass(frozen=True, slots=True)
class AccountFilters:
    """
    Фильтр списка аккаунтов.

    ``email_contains`` и ``display_name_contains`` — подстрока без учёта регистра, ``role`` — точное значение;
    ``None`` — без фильтра. Удалённые аккаунты попадают в список только при ``include_deleted``.
    """

    email_contains: str | None
    display_name_contains: str | None
    role: str | None
    marketing_emails_consent: bool | None
    include_deleted: bool


@dataclass(frozen=True, slots=True)
class AccountListItem:
    """
    Аккаунт — строка выдачи списка.

    Колонки учётной записи и профиля пусты, пока соответствующий снимок не дошёл до проекции.
    """

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


class AccountRepositoryPort(Protocol):
    """Контракт хранилища строк списка аккаунтов, на который опирается application-слой."""

    async def upsert_account_auth_part(self, *, user_id: UUID, auth_part: AccountAuthPart) -> None:
        """
        Записывает колонки учётной записи; строки нет — создаёт её без колонок профиля.

        Снимок не новее уже записанного пропускается молча: снимки приходят не по порядку и повторно.

        Scenarios:
            - любое изменение учётной записи: регистрация, подтверждение email

        Args:
            user_id: Id аккаунта
            auth_part: Колонки учётной записи и версия снимка
        """
        ...

    async def upsert_account_profile_part(self, *, user_id: UUID, profile_part: AccountProfilePart) -> None:
        """
        Записывает колонки профиля; строки нет — создаёт её без колонок учётной записи.

        Снимок не новее уже записанного пропускается молча: снимки приходят не по порядку и повторно.

        Scenarios:
            - любое изменение профиля: регистрация, правка имени, подписка на рассылку или отказ от неё

        Args:
            user_id: Id аккаунта
            profile_part: Колонки профиля и версия снимка
        """
        ...

    async def find_accounts_page(
        self,
        *,
        page: OffsetPageQuery,
        filters: AccountFilters,
        sort_direction: SortDirectionEnum,
    ) -> OffsetPage[AccountListItem]:
        """
        Возвращает страницу списка аккаунтов под фильтром и число всех аккаунтов под ним.

        Порядок — по дате регистрации в заданном направлении; аккаунты, чья учётная запись ещё не дошла до
        проекции, — в конце при любом направлении.

        Scenarios:
            - админский раздел «Аккаунты»

        Args:
            page: Номер страницы и её размер
            filters: Подстроки email и имени, роль, согласие на рассылку, показ удалённых
            sort_direction: Направление сортировки по дате регистрации

        Returns:
            Аккаунты страницы и их общее число под фильтром
        """
        ...
