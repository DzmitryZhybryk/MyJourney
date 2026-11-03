from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.repositories.base_repository import BaseDBRepository
from app.users.application.ports.user_repository import UserRepositoryPort
from app.users.domain.entities import UserEntity
from app.users.infra.models import User


class UserRepository(BaseDBRepository[User], UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=User)

    async def insert_user(self, user_entity: UserEntity) -> None:
        await self.insert(data=self._to_model(user_entity=user_entity))

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

    def _to_model(self, user_entity: UserEntity) -> User:
        return User(
            id=user_entity.user_id,
            display_name=user_entity.display_name,
            terms_accepted_at=user_entity.terms_accepted_at,
            marketing_emails_consent=user_entity.marketing_emails_consent,
            created_at=user_entity.created_at,
            updated_at=user_entity.updated_at,
            deleted_at=user_entity.deleted_at,
        )
