from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


class BaseUnitOfWork:
    """
    Базовый Unit Of Work поверх SA-сессии — тонкий транзакционный фасад.

    Жизненным циклом сессии владеет ``db_session_dependency``
    (``async with sessionmaker() as session``): он открывает сессию на запрос и
    закрывает её на выходе. UoW сессию НЕ открывает и НЕ закрывает — он лишь
    группирует репозитории и задаёт транзакционную область.

    Транзакционная модель (Option A): один use-case = одна область
    ``async with uow.transaction():`` во владении входной точки use-case'а
    (например, ``AuthService.register``). Внутри области явный ``await uow.commit()``
    фиксирует изменения; cross-domain участники (``UserService.create_user``) не
    коммитят — их записи фиксируются тем же единственным commit'ом атомарно.

    Два уровня явности границы транзакции:
      * ``transaction()`` — ОБЛАСТЬ (видна по ``async with``-блоку и отступу).
        Выход без commit'а ИЛИ исключение → rollback всего незакоммиченного.
      * ``commit()`` — ДЕЙСТВИЕ (явная фиксация «транзакция завершена»).

    Доменные UoW наследуются и инициализируют репозитории в ``__init__``.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        """
        Явная транзакционная область поверх request-scoped сессии.

        Внутри блока вызывается ``await uow.commit()`` — явная фиксация. Выход из
        блока без commit'а ИЛИ исключение → ``rollback`` (всё незакоммиченное
        откатывается); после успешного commit'а ``rollback`` на выходе — no-op
        (зафиксированное уже не отменить). Сессию НЕ создаёт и НЕ закрывает —
        её lifecycle за ``db_session_dependency``.

        Scenarios:
            - любой use case, который работает с базой через UnitOfWork
        """
        try:
            yield
        finally:
            await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        """
        Доступ к async-сессии для интеграций, требующих raw-сессии.

        Не использовать в обычной бизнес-логике — все DB-операции должны
        идти через репозитории.

        Scenarios:
            - use case, который ставит фоновую задачу атомарно со своими записями
        """
        return self._session

    async def flush(self) -> None:
        """
        Материализует pending-изменения в БД в рамках текущей транзакции, без commit'а.

        Нужен, когда в одной транзакции дочерняя запись ссылается по FK на родителя,
        добавленного ранее в той же транзакции: явный ``flush()`` после вставки
        родителя отправляет его INSERT в БД до зависимой строки и исключает
        ``ForeignKeyViolation``. Порядок INSERT'ов между разными мапперами в одном
        flush SQLAlchemy не гарантирует, а relationship между ними ради ordering'а
        мы намеренно не заводим. Изменения остаются невидимыми другим транзакциям
        до ``commit()``.

        Scenarios:
            - use case, который в одной транзакции вставляет родителя и ссылающуюся на него запись
        """
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
