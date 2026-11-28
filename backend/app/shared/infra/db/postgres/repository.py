from typing import Any, cast

from sqlalchemy import CursorResult, Select, Update, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.postgres.exceptions import StaleRowVersionError
from app.shared.infra.db.postgres.models import BaseDBModel
from app.shared.pagination.offset import OffsetPageQuery


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

    async def _fetch_offset_page(
        self,
        *,
        query: Select[ModelT],
        page: OffsetPageQuery,
    ) -> tuple[tuple[ModelT, ...], int]:
        """
        Выполняет запрос списка постранично по номеру страницы и считает все его строки.

        Scenarios:
            - любая таблица с номерами страниц и общим числом строк

        Args:
            query: SELECT списка с фильтрами и сортировкой, без ``LIMIT``/``OFFSET``
            page: Номер страницы и её размер

        Returns:
            Модели страницы и число всех строк запроса; страница за концом списка — пустой кортеж
        """
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total = (await self._session.execute(count_query)).scalar_one()
        page_query = query.limit(page.limit).offset((page.page - 1) * page.limit)
        page_models = await self._session.scalars(page_query)
        return tuple(page_models), total

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

    async def _execute_versioned_update(self, query: Update) -> None:
        """
        Выполняет UPDATE одной строки, в чьём WHERE уже стоят ключ и ожидаемая версия.

        Scenarios:
            - запись изменённой сущности с версией в любом репозитории

        Args:
            query: UPDATE, ограниченный ключом строки и её ожидаемой версией

        Raises:
            StaleRowVersionError: Ни одна строка не обновилась — версия в базе другая или строки нет
        """
        # Для UPDATE сессия возвращает CursorResult, но её аннотации обещают только общий Result, поэтому cast.
        result = cast(CursorResult[Any], await self._session.execute(query))
        if result.rowcount == 0:
            raise StaleRowVersionError()
