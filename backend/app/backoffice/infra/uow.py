from sqlalchemy.ext.asyncio import AsyncSession

from app.backoffice.application.ports.account_repository import AccountRepositoryPort
from app.backoffice.application.ports.unit_of_work import BackofficeUnitOfWorkPort
from app.backoffice.infra.repositories import AccountRepository
from app.shared.infra.db.postgres.uow import BaseUnitOfWork


class BackofficeUnitOfWork(BaseUnitOfWork, BackofficeUnitOfWorkPort):
    account_repository: AccountRepositoryPort

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.account_repository = AccountRepository(session)
