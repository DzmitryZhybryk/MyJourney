"""Протоколы выпуска access-токенов."""

from typing import Protocol
from uuid import UUID


class AccessTokenIssuerPort(Protocol):
    """
    Протокол подписи access-токена.

    Выпуск отделён от проверки: тому, кто выдаёт токены, проверка не нужна, а значит и
    зависимость от неё.
    """

    def create_access_token(self, *, user_id: UUID, role: str, email_verified: bool) -> str:
        """
        Подписывает access-токен пользователя.

        Scenarios:
            - домен, который выдаёт пару токенов: регистрация, вход, обновление сессии

        Args:
            user_id: Владелец токена, попадает в claim ``sub``
            role: Роль пользователя
            email_verified: Подтверждён ли email

        Returns:
            Подписанный JWT
        """
        ...
