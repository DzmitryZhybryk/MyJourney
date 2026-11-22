from typing import Annotated
from uuid import UUID

from pydantic import ConfigDict, Field

from app.shared.schemas.base import CamelModel


class FindAccountsByIdsRequest(CamelModel):
    """Id учётных записей (query-параметры): ``ids`` повторяется по разу на id, повторы схлопываются."""

    ids: Annotated[frozenset[UUID], Field(min_length=1, max_length=100)]


class AccountItem(CamelModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str
    is_deleted: bool


class AccountsResponse(CamelModel):
    """Найденные учётные записи в произвольном порядке; id без записи в ответе нет."""

    model_config = ConfigDict(frozen=True)

    accounts: tuple[AccountItem, ...]
