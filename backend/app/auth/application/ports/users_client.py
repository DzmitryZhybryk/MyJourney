import datetime as dt
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

__all__ = ["CreateUserRequest", "UsersClientPort"]


@dataclass(frozen=True, slots=True)
class CreateUserRequest:
    """
    Что auth отправляет users при регистрации пользователя.

    Свой тип даже при совпадении полей с командой users: фиксирует набор полей, который
    отправляет auth, и не пускает изменения схемы users в код auth.
    """

    user_id: UUID
    display_name: str
    marketing_emails_consent: bool
    terms_accepted_at: dt.datetime


class UsersClientPort(Protocol):
    """Контракт исходящего вызова users-сервиса для регистрации пользователя."""

    async def create_user(self, request: CreateUserRequest) -> None: ...
