from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.settings import PostgresSettings


# SessionMaker используется как ключ в ComponentRegistry для типобезопасного доступа
# Это позволяет использовать registry.get(SessionMaker) вместо строковых ключей
class SessionMaker(async_sessionmaker[AsyncSession]):
    pass


class SqlAlchemyComponent(BaseComponent):
    def __init__(self, settings: PostgresSettings) -> None:
        self._engine = create_async_engine(settings.postgres_dsn, **settings.engine_kwargs)
        self._session_maker = SessionMaker(self._engine, **settings.sessionmaker_kwargs)

    async def startup(self, registry: ComponentRegistry) -> None:
        registry.set(key=SessionMaker, value=self._session_maker)

    async def shutdown(self) -> None:
        await self._engine.dispose()
