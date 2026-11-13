from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AccessTokenPayload(BaseModel):
    """
    Payload access-токена в том виде, в каком он лежит в JWT: одна форма и для выпуска, и для разбора.

    Строгий режим: claim неверного типа — ошибка, а не молчаливое приведение. Отсутствующий
    ``permissions`` (токен выпущен до появления прав) — пустой список.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    # Строгий режим не принимает UUID строкой, а в JWT он всегда строка.
    sub: Annotated[UUID, Field(strict=False)]
    role: str
    plan: str
    email_verified: bool
    permissions: list[str] = Field(default_factory=list)
    iat: int
    exp: int
