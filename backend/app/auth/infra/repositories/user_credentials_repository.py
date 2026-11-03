from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports.user_credentials_repository import UserCredentialsRepositoryPort
from app.auth.domain.entities import UserCredentialsEntity
from app.auth.domain.enums import UserRoleEnum
from app.auth.domain.value_objects import Password
from app.auth.infra.models import UserCredentials
from app.shared.repositories.base_repository import BaseDBRepository
from app.shared.types import DictStrAny


class UserCredentialsRepository(BaseDBRepository[UserCredentials], UserCredentialsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализирует репозиторий учётных данных пользователей.

        Args:
            session: Асинхронная SQLAlchemy-сессия, привязанная к UnitOfWork
        """
        super().__init__(session=session, model=UserCredentials)

    async def insert_user_credentials(self, user_credentials_entity: UserCredentialsEntity) -> None:
        """
        Добавляет учётные данные пользователя в сессию без коммита.

        Запись становится видимой другим транзакциям только после ``commit()``
        в UnitOfWork. Уникальные индексы по ``lower(email)`` и ``lower(username)``
        могут выбросить ``IntegrityError`` на flush, если конфликт не был отловлен
        предварительной проверкой.

        Args:
            user_credentials_entity: Доменная сущность учётных данных
        """
        await self.insert(data=UserCredentials(**self._to_columns(user_credentials_entity=user_credentials_entity)))

    async def update_user_credentials_by_user_id(self, user_credentials_entity: UserCredentialsEntity) -> None:
        """
        Персистит изменённое состояние учётных данных через atomic UPDATE по PK.

        Все non-PK-поля переписываются текущим состоянием credentials.

        Args:
            user_credentials_entity: Доменная сущность с уже обновлённым состоянием
        """
        values = self._to_columns(user_credentials_entity=user_credentials_entity)
        del values["user_id"]  # PK не входит в SET
        query = (
            sa.update(UserCredentials)
            .where(UserCredentials.user_id == user_credentials_entity.user_id)
            .values(**values)
        )
        await self._session.execute(query)

    async def find_user_credentials_by_user_id(self, user_id: UUID) -> UserCredentialsEntity | None:
        """
        Загружает учётные данные пользователя по его PK.

        Args:
            user_id: UUID пользователя

        Returns:
            Доменная сущность учётных данных либо ``None``, если запись не найдена
        """
        query = sa.select(UserCredentials).where(UserCredentials.user_id == user_id)
        user_credentials_model = await self._fetch_one(query=query)
        return self._to_entity(user_credentials_model=user_credentials_model) if user_credentials_model else None

    async def find_user_credentials_by_email(self, email: str) -> UserCredentialsEntity | None:
        """
        Загружает учётные данные по email без учёта регистра.

        Args:
            email: Email в любом регистре

        Returns:
            Доменная сущность учётных данных либо ``None``, если запись не найдена
        """
        query = sa.select(UserCredentials).where(sa.func.lower(UserCredentials.email) == sa.func.lower(email))
        user_credentials_model = await self._fetch_one(query=query)
        return self._to_entity(user_credentials_model=user_credentials_model) if user_credentials_model else None

    async def find_user_credentials_by_username(self, username: str) -> UserCredentialsEntity | None:
        """
        Загружает учётные данные по username без учёта регистра.

        Args:
            username: Username в любом регистре

        Returns:
            Доменная сущность учётных данных либо ``None``, если запись не найдена
        """
        query = sa.select(UserCredentials).where(sa.func.lower(UserCredentials.username) == sa.func.lower(username))
        user_credentials_model = await self._fetch_one(query=query)
        return self._to_entity(user_credentials_model=user_credentials_model) if user_credentials_model else None

    async def find_user_credentials_by_login(self, login: str) -> UserCredentialsEntity | None:
        """
        Загружает учётные данные по логину — email или username, без учёта регистра.

        Один запрос при любом исходе, чтобы время ответа login не выдавало, нашёлся ли
        аккаунт и по какому полю. Если строка — чей-то email и одновременно чужой username,
        возвращается владелец email.

        Args:
            login: Email или username в любом регистре

        Returns:
            Доменная сущность учётных данных либо ``None``, если запись не найдена
        """
        login_lower = sa.func.lower(login)
        email_matches = sa.func.lower(UserCredentials.email) == login_lower
        query = (
            sa.select(UserCredentials)
            .where(email_matches | (sa.func.lower(UserCredentials.username) == login_lower))
            .order_by(email_matches.desc())
            .limit(1)
        )
        user_credentials_model = await self._fetch_one(query=query)
        return self._to_entity(user_credentials_model=user_credentials_model) if user_credentials_model else None

    def _to_columns(self, user_credentials_entity: UserCredentialsEntity) -> DictStrAny:
        """
        Единый маппинг credentials → колонки ORM-модели (включая PK ``user_id``).

        Источник истины для обоих путей записи: INSERT (``UserCredentials(**columns)``)
        и UPDATE (те же колонки минус PK). Новое поле добавляется здесь один раз —
        и попадает и в INSERT, и в UPDATE, рассинхрон между ними невозможен.

        Scenarios:
            - регистрация
            - верный код в диалоге «Подтвердите email»

        Args:
            user_credentials_entity: Доменная сущность учётных данных

        Returns:
            Словарь ``column -> value`` со всеми колонками, включая PK
        """
        return {
            "user_id": user_credentials_entity.user_id,
            "email": user_credentials_entity.email,
            "username": user_credentials_entity.username,
            "password_hash": user_credentials_entity.password.hash,
            "role": user_credentials_entity.role.value,
            "email_verified_at": user_credentials_entity.email_verified_at,
            "created_at": user_credentials_entity.created_at,
            "updated_at": user_credentials_entity.updated_at,
            "deleted_at": user_credentials_entity.deleted_at,
        }

    def _to_entity(self, user_credentials_model: UserCredentials) -> UserCredentialsEntity:
        """
        Конвертирует ORM-модель в доменную сущность учётных данных.

        Scenarios:
            - регистрация: проверка, что email и username свободны
            - вход и обновление сессии
            - отправка и ввод кода в диалоге «Подтвердите email»
            - данные входа текущего пользователя

        Args:
            user_credentials_model: ORM-модель из БД

        Returns:
            Доменная сущность учётных данных
        """
        return UserCredentialsEntity(
            user_id=user_credentials_model.user_id,
            email=user_credentials_model.email,
            username=user_credentials_model.username,
            password=Password(hash=user_credentials_model.password_hash),
            role=UserRoleEnum(user_credentials_model.role),
            email_verified_at=user_credentials_model.email_verified_at,
            created_at=user_credentials_model.created_at,
            updated_at=user_credentials_model.updated_at,
            deleted_at=user_credentials_model.deleted_at,
        )
