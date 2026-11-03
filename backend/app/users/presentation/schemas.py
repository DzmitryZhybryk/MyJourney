from pydantic import ConfigDict

from app.shared.schemas.base import CamelModel


class CurrentUserResponse(CamelModel):
    model_config = ConfigDict(frozen=True)

    display_name: str
