import datetime as dt
from dataclasses import dataclass
from uuid import UUID

__all__ = ["CreateUserCommand", "UpdateCurrentUserCommand"]


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    user_id: UUID
    display_name: str
    marketing_emails_consent: bool
    terms_accepted_at: dt.datetime


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserCommand:
    display_name: str | None = None
    marketing_emails_consent: bool | None = None
