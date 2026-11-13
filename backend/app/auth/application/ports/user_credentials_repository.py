from typing import Protocol
from uuid import UUID

from app.auth.domain.entities import UserCredentialsEntity

__all__ = ["UserCredentialsRepositoryPort"]


class UserCredentialsRepositoryPort(Protocol):
    """Контракт хранилища учётных данных, на который опирается application-слой."""

    async def insert_user_credentials(self, user_credentials_entity: UserCredentialsEntity) -> None:
        """
        Добавляет учётные данные; email и username уникальны без учёта регистра.

        Scenarios:
            - регистрация

        Args:
            user_credentials_entity: Новые учётные данные
        """
        ...

    async def update_user_credentials_by_user_id(self, user_credentials_entity: UserCredentialsEntity) -> None:
        """
        Записывает изменённое состояние учётных данных.

        Scenarios:
            - верный код в диалоге «Подтвердите email»

        Args:
            user_credentials_entity: Учётные данные с уже изменённым состоянием
        """
        ...

    async def find_user_credentials_by_user_id(self, user_id: UUID) -> UserCredentialsEntity | None:
        """
        Находит учётные данные по id пользователя.

        Scenarios:
            - обновление сессии
            - отправка и ввод кода в диалоге «Подтвердите email»
            - данные входа текущего пользователя

        Args:
            user_id: Id пользователя

        Returns:
            Учётные данные; ``None``, если их нет
        """
        ...

    async def find_user_credentials_by_email(self, email: str) -> UserCredentialsEntity | None:
        """
        Находит учётные данные по email без учёта регистра.

        Scenarios:
            - регистрация: email не должен быть занят

        Args:
            email: Email

        Returns:
            Учётные данные; ``None``, если email свободен
        """
        ...

    async def find_user_credentials_by_username(self, username: str) -> UserCredentialsEntity | None:
        """
        Находит учётные данные по username без учёта регистра.

        Scenarios:
            - регистрация: username не должен быть занят

        Args:
            username: Username

        Returns:
            Учётные данные; ``None``, если username свободен
        """
        ...

    async def find_user_credentials_by_login(self, login: str) -> UserCredentialsEntity | None:
        """
        Находит учётные данные по логину — email или username, без учёта регистра.

        Scenarios:
            - вход

        Args:
            login: Email или username

        Returns:
            Учётные данные; ``None``, если такого логина нет
        """
        ...
