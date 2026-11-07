from typing import Annotated

from pydantic import ConfigDict, StringConstraints
from pydantic.experimental.missing_sentinel import MISSING

from app.shared.schemas.base import CamelModel


class CurrentUserResponse(CamelModel):
    model_config = ConfigDict(frozen=True)

    display_name: str
    marketing_emails_consent: bool


class UpdateCurrentUserRequest(CamelModel):
    """
    Поля профиля, которые меняются. Отсутствующее поле не меняется; ``null`` — 422.
    """

    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)] | MISSING = (
        MISSING
    )
    marketing_emails_consent: bool | MISSING = MISSING
