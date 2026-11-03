from typing import Protocol
from uuid import UUID

from app.auth.domain.entities import RefreshTokenEntity

__all__ = ["RefreshTokenRepositoryPort"]


class RefreshTokenRepositoryPort(Protocol):
    """Контракт хранилища refresh-токенов, на который опирается application-слой."""

    async def insert_refresh_token(self, refresh_token_entity: RefreshTokenEntity) -> None:
        """
        Добавляет refresh-токен.

        Scenarios:
            - регистрация
            - вход
            - обновление сессии: новый токен вместо старого

        Args:
            refresh_token_entity: Новый refresh-токен
        """
        ...

    async def find_refresh_token_by_hash_for_update(self, token_hash: str) -> RefreshTokenEntity | None:
        """
        Находит refresh-токен по hash'у секрета и блокирует строку до конца транзакции.

        Scenarios:
            - выход из аккаунта
            - обновление сессии

        Args:
            token_hash: Детерминированный hash секрета из cookie

        Returns:
            Refresh-токен; ``None``, если такого нет
        """
        ...

    async def update_refresh_token_by_id(self, refresh_token_entity: RefreshTokenEntity) -> None:
        """
        Записывает изменённое состояние refresh-токена.

        Scenarios:
            - выход из аккаунта
            - обновление сессии: старый токен отзывается

        Args:
            refresh_token_entity: Refresh-токен с уже изменённым состоянием
        """
        ...

    async def revoke_all_active_refresh_tokens_by_user_id(self, user_id: UUID) -> None:
        """
        Отзывает все активные refresh-токены пользователя.

        Scenarios:
            - обновление сессии отозванным токеном: признак утечки, все сессии пользователя завершаются

        Args:
            user_id: Владелец токенов
        """
        ...
