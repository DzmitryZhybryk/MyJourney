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
            - приветствие на главной и имя в меню профиля в шапке

        Args:
            user_id: Id пользователя

        Returns:
            Пользователь; ``None``, если его нет
        """
        ...
