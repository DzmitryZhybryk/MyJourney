from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.backoffice.application.services.account import AccountService
from app.backoffice.infra.uow import BackofficeUnitOfWork
from app.shared.infra.db.postgres.dependency import db_session_dependency


def backoffice_uow_dependency(
    session: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> BackofficeUnitOfWork:
    return BackofficeUnitOfWork(session)


def account_service_dependency(
    uow: Annotated[BackofficeUnitOfWork, Depends(backoffice_uow_dependency)],
) -> AccountService:
    return AccountService(uow)
