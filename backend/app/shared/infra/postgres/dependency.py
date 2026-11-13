"""FastAPI-зависимости для работы с SA-сессией."""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.postgres.component import SessionMaker
from app.shared.schemas.base import BFastAPI

__all__ = [
    "db_session_dependency",
]


async def db_session_dependency(request: Request) -> AsyncGenerator[AsyncSession]:
    """
    Общая зависимость для получения сессии БД.

    Scenarios:
        - любой запрос, который работает с базой: одна сессия на запрос
    """
    app: BFastAPI = request.app
    sessionmaker = app.registry.get(SessionMaker)
    async with sessionmaker() as session:
        yield session
