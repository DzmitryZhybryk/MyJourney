from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models import BaseDBModel


class BaseDBRepository[ModelT: BaseDBModel]:
    """Базовый асинхронный репозиторий поверх SQLAlchemy-сессии."""

    def __init__(self, *, session: AsyncSession, model: type[ModelT]) -> None:
        """
        Инициализирует репозиторий.

        Args:
            session: Асинхронная SQLAlchemy-сессия, привязанная к UnitOfWork
            model: Класс ORM-модели, с которой работает репозиторий
        """
        self._session = session
        self._model = model

    async def _fetch_one(self, query: Select[ModelT]) -> ModelT | None:
        """
        Выполняет запрос и возвращает одну модель или ``None``.

        Scenarios:
            - поиск одной строки в любом репозитории

        Args:
            query: SELECT-запрос, возвращающий не более одной строки

        Returns:
            Найденная модель либо ``None``, если запись не найдена
        """
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def insert(self, data: ModelT) -> None:
        """
        Добавляет модель в сессию без коммита.

        Реальная вставка в БД произойдёт на ближайшем flush, а видимой другим
        транзакциям запись станет только после ``commit()`` в UnitOfWork.

        Scenarios:
            - добавление строки в любом репозитории

        Args:
            data: Экземпляр ORM-модели для вставки
        """
        self._session.add(data)
