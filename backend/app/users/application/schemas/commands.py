import datetime as dt
from dataclasses import dataclass
from uuid import UUID

__all__ = ["CreateUserCommand"]


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    user_id: UUID
    display_name: str
    marketing_emails_consent: bool
    terms_accepted_at: dt.datetime
