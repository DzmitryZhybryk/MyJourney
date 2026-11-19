from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.repositories.base_repository import BaseDBRepository
from app.shared.types import DictStrAny
from app.users.application.ports.user_repository import UserRepositoryPort
from app.users.domain.entities import UserEntity
from app.users.infra.models import User


class UserRepository(BaseDBRepository[User], UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=User)

    async def insert_user(self, user_entity: UserEntity) -> None:
        await self.insert(data=User(**self._to_columns(user_entity=user_entity)))

    async def update_user_by_id(self, user_entity: UserEntity) -> None:
        """
        Персистит изменённое состояние пользователя через atomic UPDATE по PK.

        Все non-PK-поля переписываются текущим состоянием пользователя. Под ранее взятым
        ``FOR UPDATE``-локом параллельные апдейты сериализованы.

        Args:
            user_entity: Доменная сущность с уже обновлённым состоянием
        """
        values = self._to_columns(user_entity=user_entity)
        del values["id"]
        query = update(User).where(User.id == user_entity.user_id).values(**values)
        await self._session.execute(query)

    async def find_user_by_id_for_update(self, user_id: UUID) -> UserEntity | None:
        """
        Возвращает пользователя по идентификатору и блокирует строку до конца транзакции.

        Soft-deleted записи НЕ фильтруются, как и в ``find_user_by_id``.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Доменная сущность пользователя либо ``None``, если запись не найдена
        """
        query = select(User).where(User.id == user_id).with_for_update()
        user_model = await self._fetch_one(query=query)
        return self._to_entity(user_model=user_model) if user_model else None

    async def find_user_by_id(self, user_id: UUID) -> UserEntity | None:
        """
        Возвращает пользователя по идентификатору.

        Soft-deleted записи НЕ фильтруются: репозиторий отдаёт то, что лежит
        в хранилище, а интерпретация удаления — забота домена (``is_deleted``).

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Доменная сущность пользователя либо ``None``, если запись не найдена
        """
        query = select(User).where(User.id == user_id)
        user_model = await self._fetch_one(query=query)
        return self._to_entity(user_model=user_model) if user_model else None

    def _to_entity(self, user_model: User) -> UserEntity:
        return UserEntity(
            user_id=user_model.id,
            display_name=user_model.display_name,
            terms_accepted_at=user_model.terms_accepted_at,
            marketing_emails_consent=user_model.marketing_emails_consent,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
            deleted_at=user_model.deleted_at,
        )

    def _to_columns(self, user_entity: UserEntity) -> DictStrAny:
        """
        Единый маппинг пользователя → колонки ORM-модели (включая PK ``id``).

        Источник истины для обоих путей записи: INSERT (``User(**columns)``)
        и UPDATE (те же колонки минус PK). Новое поле добавляется здесь один раз —
        и попадает и в INSERT, и в UPDATE, рассинхрон между ними невозможен.

        Scenarios:
            - регистрация
            - правка профиля на странице профиля

        Args:
            user_entity: Доменная сущность пользователя

        Returns:
            Словарь ``column -> value`` со всеми колонками, включая PK
        """
        return {
            "id": user_entity.user_id,
            "display_name": user_entity.display_name,
            "terms_accepted_at": user_entity.terms_accepted_at,
            "marketing_emails_consent": user_entity.marketing_emails_consent,
            "created_at": user_entity.created_at,
            "updated_at": user_entity.updated_at,
            "deleted_at": user_entity.deleted_at,
        }
