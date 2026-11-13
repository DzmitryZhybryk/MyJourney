"""Протоколы выпуска access-токенов."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """
    Содержимое access-токена.

    Attributes:
        user_id: Владелец токена, попадает в claim ``sub``
        role: Роль пользователя
        plan: Тариф пользователя
        permissions: Раскрытые права — по ним маршруты решают, пускать ли запрос
        email_verified: Подтверждён ли email
    """

    user_id: UUID
    role: str
    plan: str
    permissions: frozenset[str]
    email_verified: bool


class AccessTokenIssuerPort(Protocol):
    """
    Протокол подписи access-токена.

    Выпуск отделён от проверки: тому, кто выдаёт токены, проверка не нужна, а значит и
    зависимость от неё.
    """

    def create_access_token(self, *, claims: AccessTokenClaims) -> str:
        """
        Подписывает access-токен пользователя.

        Scenarios:
            - домен, который выдаёт пару токенов: регистрация, вход, обновление сессии

        Args:
            claims: Содержимое токена

        Returns:
            Подписанный JWT
        """
        ...
