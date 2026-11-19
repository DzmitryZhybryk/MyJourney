import datetime as dt
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.ports.refresh_token_repository import RefreshTokenRepositoryPort
from app.auth.domain.entities import RefreshTokenEntity
from app.auth.infra.models import RefreshToken
from app.shared.repositories.base_repository import BaseDBRepository
from app.shared.types import DictStrAny


class RefreshTokenRepository(BaseDBRepository[RefreshToken], RefreshTokenRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализирует репозиторий refresh-токенов.

        Args:
            session: Асинхронная SQLAlchemy-сессия, привязанная к UnitOfWork
        """
        super().__init__(session=session, model=RefreshToken)

    async def insert_refresh_token(self, refresh_token_entity: RefreshTokenEntity) -> None:
        """
        Добавляет refresh-токен в сессию без коммита.

        Запись становится видимой другим транзакциям только после ``commit()``
        в UnitOfWork.

        Args:
            refresh_token_entity: Доменная сущность refresh-токена
        """
        await self.insert(data=RefreshToken(**self._to_columns(refresh_token_entity=refresh_token_entity)))

    async def find_refresh_token_by_hash_for_update(self, token_hash: str) -> RefreshTokenEntity | None:
        """
        Находит refresh-токен по hash'у и блокирует строку до конца транзакции.

        ``SELECT ... FOR UPDATE`` нужен для refresh-флоу: гарантирует, что
        параллельные запросы /refresh с одним и тем же secret сериализуются
        и второй увидит уже revoked-состояние, что триггерит reuse detection.

        Args:
            token_hash: Детерминированный hash plaintext-секрета из cookie

        Returns:
            Доменная сущность refresh-токена либо ``None``, если запись не найдена
        """
        query = sa.select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        refresh_token_model = await self._fetch_one(query=query)
        return self._to_entity(refresh_token_model=refresh_token_model) if refresh_token_model else None

    async def update_refresh_token_by_id(self, refresh_token_entity: RefreshTokenEntity) -> None:
        """
        Персистит изменённое состояние refresh-токена через atomic UPDATE по PK.

        Все non-PK-поля переписываются текущим состоянием refresh_token. Под ранее взятым
        ``FOR UPDATE``-локом параллельные апдейты сериализованы.

        Args:
            refresh_token_entity: Доменная сущность с уже обновлённым состоянием
        """
        values = self._to_columns(refresh_token_entity=refresh_token_entity)
        del values["id"]  # PK не входит в SET
        query = sa.update(RefreshToken).where(RefreshToken.id == refresh_token_entity.token_id).values(**values)
        await self._session.execute(query)

    async def revoke_all_active_refresh_tokens_by_user_id(self, user_id: UUID) -> None:
        """
        Bulk-revoke всех активных refresh-токенов пользователя.

        Используется для reuse detection (OAuth 2.1): если на /refresh пришёл
        уже revoked-секрет — это сигнал компрометации, и все остальные
        активные сессии пользователя инвалидируются.

        Args:
            user_id: ID пользователя, чьи активные токены отзываем
        """
        now = dt.datetime.now(tz=dt.UTC)
        query = (
            sa.update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now, updated_at=now)
        )
        await self._session.execute(query)

    def _to_columns(self, refresh_token_entity: RefreshTokenEntity) -> DictStrAny:
        """
        Единый маппинг refresh_token → колонки ORM-модели (включая PK ``id``).

        Источник истины для обоих путей записи: INSERT (``RefreshToken(**columns)``)
        и UPDATE (те же колонки минус PK). Новое поле добавляется здесь один раз —
        и попадает и в INSERT, и в UPDATE, рассинхрон между ними невозможен.

        Scenarios:
            - регистрация и вход
            - выход из аккаунта
            - обновление сессии

        Args:
            refresh_token_entity: Доменная сущность refresh-токена

        Returns:
            Словарь ``column -> value`` со всеми колонками, включая PK
        """
        return {
            "id": refresh_token_entity.token_id,
            "user_id": refresh_token_entity.user_id,
            "token_hash": refresh_token_entity.token_hash,
            "expires_at": refresh_token_entity.expires_at,
            "revoked_at": refresh_token_entity.revoked_at,
            "ip_address": refresh_token_entity.ip_address,
            "user_agent": refresh_token_entity.user_agent,
            "created_at": refresh_token_entity.created_at,
            "updated_at": refresh_token_entity.updated_at,
            "deleted_at": refresh_token_entity.deleted_at,
        }

    def _to_entity(self, refresh_token_model: RefreshToken) -> RefreshTokenEntity:
        """
        Конвертирует ORM-модель в доменную сущность.

        Scenarios:
            - выход из аккаунта
            - обновление сессии

        Args:
            refresh_token_model: ORM-модель из БД

        Returns:
            Доменная сущность refresh-токена
        """
        return RefreshTokenEntity(
            token_id=refresh_token_model.id,
            user_id=refresh_token_model.user_id,
            token_hash=refresh_token_model.token_hash,
            expires_at=refresh_token_model.expires_at,
            revoked_at=refresh_token_model.revoked_at,
            ip_address=refresh_token_model.ip_address,
            user_agent=refresh_token_model.user_agent,
            created_at=refresh_token_model.created_at,
            updated_at=refresh_token_model.updated_at,
            deleted_at=refresh_token_model.deleted_at,
        )
