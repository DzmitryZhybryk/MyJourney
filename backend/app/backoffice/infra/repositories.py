from uuid import UUID

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.backoffice.application.ports.account_repository import (
    AccountAuthPart,
    AccountFilters,
    AccountListItem,
    AccountProfilePart,
    AccountRepositoryPort,
)
from app.backoffice.infra.models import Account
from app.shared.enums import SortDirectionEnum
from app.shared.infra.db.postgres.expressions import directed_order
from app.shared.infra.db.postgres.repository import BaseDBRepository
from app.shared.pagination.offset import OffsetPage, OffsetPageQuery


class AccountRepository(BaseDBRepository[Account], AccountRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Account)

    async def upsert_account_auth_part(self, *, user_id: UUID, auth_part: AccountAuthPart) -> None:
        auth_columns = {
            "email": auth_part.email,
            "username": auth_part.username,
            "role": auth_part.role,
            "plan": auth_part.plan,
            "email_verified_at": auth_part.email_verified_at,
            "registered_at": auth_part.registered_at,
            "deleted_at": auth_part.deleted_at,
            "auth_version": auth_part.version,
        }
        query = insert(Account).values(user_id=user_id, **auth_columns)
        query = query.on_conflict_do_update(
            index_elements=[Account.user_id],
            set_={column_name: query.excluded[column_name] for column_name in auth_columns},
            where=or_(Account.auth_version.is_(None), Account.auth_version < query.excluded.auth_version),
        )
        await self._session.execute(query)

    async def upsert_account_profile_part(self, *, user_id: UUID, profile_part: AccountProfilePart) -> None:
        profile_columns = {
            "display_name": profile_part.display_name,
            "marketing_emails_consent": profile_part.marketing_emails_consent,
            "terms_accepted_at": profile_part.terms_accepted_at,
            "users_version": profile_part.version,
        }
        query = insert(Account).values(user_id=user_id, **profile_columns)
        query = query.on_conflict_do_update(
            index_elements=[Account.user_id],
            set_={column_name: query.excluded[column_name] for column_name in profile_columns},
            where=or_(Account.users_version.is_(None), Account.users_version < query.excluded.users_version),
        )
        await self._session.execute(query)

    async def find_accounts_page(
        self,
        *,
        page: OffsetPageQuery,
        filters: AccountFilters,
        sort_direction: SortDirectionEnum,
    ) -> OffsetPage[AccountListItem]:
        """
        Возвращает страницу списка аккаунтов под фильтром и число всех аккаунтов под ним.

        Порядок — ``registered_at`` в заданном направлении, строки без него в конце; ``user_id`` в том же
        направлении делает порядок полным, иначе строки с одной датой меняли бы места между страницами.

        Args:
            page: Номер страницы и её размер
            filters: Подстроки email и имени, роль, согласие на рассылку, показ удалённых
            sort_direction: Направление сортировки по дате регистрации

        Returns:
            Аккаунты страницы и их общее число под фильтром
        """
        conditions: list[ColumnElement[bool]] = []
        if not filters.include_deleted:
            conditions.append(Account.deleted_at.is_(None))

        if filters.email_contains is not None:
            conditions.append(Account.email.icontains(filters.email_contains, autoescape=True))

        if filters.display_name_contains is not None:
            conditions.append(Account.display_name.icontains(filters.display_name_contains, autoescape=True))

        if filters.role is not None:
            conditions.append(Account.role == filters.role)

        if filters.marketing_emails_consent is not None:
            conditions.append(Account.marketing_emails_consent == filters.marketing_emails_consent)

        query = (
            select(Account)
            .where(*conditions)
            .order_by(
                directed_order(column=Account.registered_at, direction=sort_direction).nulls_last(),
                directed_order(column=Account.user_id, direction=sort_direction),
            )
        )
        account_models, total = await self._fetch_offset_page(query=query, page=page)
        account_items = tuple(
            AccountListItem(
                user_id=account_model.user_id,
                email=account_model.email,
                username=account_model.username,
                role=account_model.role,
                plan=account_model.plan,
                email_verified_at=account_model.email_verified_at,
                registered_at=account_model.registered_at,
                deleted_at=account_model.deleted_at,
                display_name=account_model.display_name,
                marketing_emails_consent=account_model.marketing_emails_consent,
                terms_accepted_at=account_model.terms_accepted_at,
            )
            for account_model in account_models
        )
        return OffsetPage(items=account_items, total=total)
