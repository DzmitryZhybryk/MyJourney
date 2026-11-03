from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.postgres.uow import BaseUnitOfWork
from app.users.application.ports.unit_of_work import UserUnitOfWorkPort
from app.users.application.ports.user_repository import UserRepositoryPort
from app.users.infra.repositories import UserRepository


class UserUnitOfWork(BaseUnitOfWork, UserUnitOfWorkPort):
    # Атрибут типизирован портом (а не конкретным репозиторием): сервис зависит от
    # контракта, а тестовый UoW подставляет in-memory фейк того же порта.
    user_repository: UserRepositoryPort

    def __init__(self, session: AsyncSession):
        super().__init__(session=session)
        self.user_repository = UserRepository(session=session)
