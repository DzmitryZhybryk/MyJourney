import datetime as dt
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = [
    "CurrentAccountResult",
    "IssuedRefreshToken",
    "TokenPairResult",
]


@dataclass(frozen=True, slots=True)
class CurrentAccountResult:
    email: str
    username: str
    email_verified: bool


class IssuedRefreshToken(BaseModel):
    """
    Сужённый view на refresh-токен для presentation-слоя.

    Plaintext-секрет уходит в HttpOnly cookie, в БД лежит только его
    детерминированный hash. ``SecretStr`` гарантирует, что секрет не утечёт
    в логи через ``repr()`` / structlog — для извлечения нужен явный
    ``get_secret_value()`` на границе HTTP.
    """

    model_config = ConfigDict(frozen=True)

    secret: SecretStr
    expires_at: dt.datetime


class TokenPairResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: SecretStr
    refresh_token: IssuedRefreshToken
