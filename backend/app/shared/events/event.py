from pydantic import BaseModel, ConfigDict


class IntegrationEvent(BaseModel):
    """Факт, который модуль сообщает другим модулям, не зная, кто на него подписан."""

    model_config = ConfigDict(frozen=True)
