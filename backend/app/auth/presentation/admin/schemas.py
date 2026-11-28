from typing import Annotated
from uuid import UUID

from pydantic import ConfigDict, Field

from app.auth.domain.enums import UserPlanEnum, UserRoleEnum
from app.shared.schemas.base import CamelModel


class AdminFindAccountsByIdsRequest(CamelModel):
    """Id учётных записей (query-параметры): ``ids`` повторяется по разу на id, повторы схлопываются."""

    ids: Annotated[frozenset[UUID], Field(min_length=1, max_length=100)]


class AccountItem(CamelModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str
    is_deleted: bool


class AdminAccountsResponse(CamelModel):
    """Найденные учётные записи; id без записи в ответе нет."""

    model_config = ConfigDict(frozen=True)

    accounts: frozenset[AccountItem]


class AdminAccountOptionsResponse(CamelModel):
    """Все роли и тарифы учётной записи в порядке объявления: варианты фильтра и ключи подписей."""

    model_config = ConfigDict(frozen=True)

    roles: tuple[UserRoleEnum, ...]
    plans: tuple[UserPlanEnum, ...]
