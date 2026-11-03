from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.postgres.dependency import db_session_dependency
from app.users.application.services.user import UserService
from app.users.infra.uow import UserUnitOfWork


def user_service_dependency(
    session: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> UserService:
    return UserService(uow=UserUnitOfWork(session=session))
