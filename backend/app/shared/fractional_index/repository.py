from abc import ABC, abstractmethod
from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, select

from app.shared.fractional_index.models import SortKeyModel
from app.shared.repositories.base_repository import BaseDBRepository


class BaseSortKeyRepository[ModelT: SortKeyModel, ScopeT](BaseDBRepository[ModelT], ABC):
    """
    Реализация ``SortKeyRepositoryPort`` поверх SQLAlchemy — одна на все модели с ``sort_key``.

    Наследник задаёт только область: ``_sort_key_scope`` переводит её в условия ``WHERE``
    (владелец, год, неудалённые…). Ключ блокировки выводится из области и имени таблицы.
    """

    @abstractmethod
    def _sort_key_scope(self, scope: ScopeT) -> Sequence[ColumnElement[bool]]:
        """
        Переводит область порядка в условия выборки её строк.

        Scenarios:
            - любой список с ручным порядком: блокировка области и поиск ключей в ней

        Args:
            scope: Область порядка

        Returns:
            Условия ``WHERE``, вместе выделяющие строки области
        """
        raise NotImplementedError

    async def lock_sort_keys(self, scope: ScopeT) -> None:
        lock_key = f"{self._model.__tablename__}:{scope}"
        await self._session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(lock_key, 0))))

    async def find_last_sort_key(self, scope: ScopeT) -> str | None:
        query = select(func.max(self._model.sort_key)).where(*self._sort_key_scope(scope))
        return await self._session.scalar(query)

    async def find_next_sort_key(self, *, scope: ScopeT, after_sort_key: str) -> str | None:
        query = select(func.min(self._model.sort_key)).where(
            *self._sort_key_scope(scope),
            self._model.sort_key > after_sort_key,
        )
        return await self._session.scalar(query)

    async def find_previous_sort_key(self, *, scope: ScopeT, before_sort_key: str) -> str | None:
        query = select(func.max(self._model.sort_key)).where(
            *self._sort_key_scope(scope),
            self._model.sort_key < before_sort_key,
        )
        return await self._session.scalar(query)
