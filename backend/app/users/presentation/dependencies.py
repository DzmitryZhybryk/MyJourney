from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.events import EventPublisherPort
from app.shared.events.dependency import event_publisher_dependency
from app.shared.infra.db.postgres.dependency import db_session_dependency
from app.users.application.services.user import UserService
from app.users.infra.uow import UserUnitOfWork


def user_service_dependency(
    *,
    session: Annotated[AsyncSession, Depends(db_session_dependency)],
    event_publisher: Annotated[EventPublisherPort, Depends(event_publisher_dependency)],
) -> UserService:
    return UserService(uow=UserUnitOfWork(session), event_publisher=event_publisher)
