from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = [
    "FindAccountsByIdsCommand",
    "LoginCommand",
    "RegistrationCommand",
    "VerifyEmailCommand",
]


class RegistrationCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str
    email: str
    password: SecretStr
    marketing_emails_consent: bool


class LoginCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    login: str
    password: SecretStr


class VerifyEmailCommand(BaseModel):
    """Одноразовый код, который пользователь ввёл для подтверждения email."""

    model_config = ConfigDict(frozen=True)

    code: SecretStr


@dataclass(frozen=True, slots=True)
class FindAccountsByIdsCommand:
    """Id учётных записей, которые нужно показать в админке."""

    user_ids: frozenset[UUID]
