from typing import Protocol
from uuid import UUID

from app.users.domain.entities import UserEntity

__all__ = ["UserRepositoryPort"]


class UserRepositoryPort(Protocol):
    """Контракт хранилища пользователей, на который опирается application-слой."""

    async def insert_user(self, user_entity: UserEntity) -> None: ...

    async def find_user_by_id(self, user_id: UUID) -> UserEntity | None:
        """
        Находит пользователя по id; удалённый тоже находится — что с ним делать, решает вызывающий.

        Scenarios:
            - чтение профиля: приветствие на главной, страница профиля, меню в шапке

        Args:
            user_id: Id пользователя

        Returns:
            Пользователь; ``None``, если его нет
        """
        ...

    async def find_user_by_id_for_update(self, user_id: UUID) -> UserEntity | None:
        """
        Находит пользователя по id и блокирует строку до конца транзакции; удалённый тоже находится.

        Scenarios:
            - правка профиля на странице профиля

        Args:
            user_id: Id пользователя

        Returns:
            Пользователь; ``None``, если его нет
        """
        ...

    async def update_user_by_id(self, user_entity: UserEntity) -> None:
        """
        Записывает изменённое состояние пользователя.

        Scenarios:
            - правка профиля на странице профиля

        Args:
            user_entity: Пользователь с уже изменённым состоянием
        """
        ...
