"""
Реализации шины задач на procrastinate: ``ProcrastinateTaskBus`` и
``ProcrastinateSessionBoundTaskBus``. Контракты, на которые опирается application, — в ``ports.py``.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.procrastinate.component import ProcrastinateApp
from app.shared.infra.procrastinate.ports import SessionBoundTaskBusPort, TaskBusPort


class ProcrastinateSessionBoundTaskBus(SessionBoundTaskBusPort):
    """
    Реализация ``SessionBoundTaskBusPort`` поверх procrastinate, привязанная к активной SA-сессии.

    Все операции выполняются через raw psycopg-connection сессии — попадают в ту
    же транзакцию, что и pending writes. Commit'ит ``UnitOfWork``.

    SA-сессия с psycopg3-драйвером оборачивает raw psycopg.AsyncConnection в
    ``AsyncAdapt_psycopg_connection``; raw-объект достаётся через
    ``get_raw_connection().driver_connection`` и передаётся в
    ``Task.configure(connection=...)``.
    """

    def __init__(self, *, session: AsyncSession, app: ProcrastinateApp) -> None:
        self._session = session
        self._app = app

    async def defer(self, *, task_name: str, lock: str | None = None, **task_kwargs: Any) -> None:
        """
        Атомарно ставит procrastinate-таску в той же транзакции, что и pending writes.

        Без commit'а — caller отвечает за фиксацию через ``UnitOfWork.commit()``.

        Args:
            task_name: Имя procrastinate-задачи (``@task(name=...)``). Диспатч по имени
                через ``App.configure_task`` — application не импортирует объект задачи из infra.
            lock: Lock-строка procrastinate (одновременно может выполняться только
                один job с таким lock'ом). ``None`` — без lock'а.
            **task_kwargs: Аргументы, которые получит task на исполнении.
        """
        sa_connection = await self._session.connection()
        raw_connection = await sa_connection.get_raw_connection()
        await self._app.configure_task(
            name=task_name,
            connection=raw_connection.driver_connection,
            lock=lock,
        ).defer_async(**task_kwargs)


class ProcrastinateTaskBus(TaskBusPort):
    """Реализация ``TaskBusPort`` поверх procrastinate. Defer'ы выполняются как fire-and-forget."""

    def __init__(self, *, app: ProcrastinateApp) -> None:
        self._app = app

    async def defer(self, *, task_name: str, lock: str | None = None, **task_kwargs: Any) -> None:
        """
        Defer задачи вне транзакции.

        Args:
            task_name: Имя procrastinate-задачи (``@task(name=...)``). Диспатч по имени
                через ``App.configure_task`` — application не импортирует объект задачи из infra.
            lock: Lock-строка procrastinate (одновременно может выполняться только
                один job с таким lock'ом). ``None`` — без lock'а.
            **task_kwargs: Аргументы, которые получит task на исполнении.
        """
        await self._app.configure_task(name=task_name, lock=lock).defer_async(**task_kwargs)

    def bind_to(self, session: AsyncSession) -> SessionBoundTaskBusPort:
        """
        Возвращает view, привязанный к активной SA-сессии.

        Все defer'ы через возвращённый объект выполняются в той же транзакции,
        что и pending writes сессии. Используется в сервисах:

            async with uow.transaction():
                await self._task_bus.bind_to(uow.session).defer(task_name=..., **kwargs)
                await uow.commit()  # один commit фиксирует и writes, и procrastinate-job

        Args:
            session: Активная async-сессия SQLAlchemy.

        Returns:
            ``SessionBoundTaskBusPort``, в котором ``defer(...)`` атомарен с сессией.
        """
        return ProcrastinateSessionBoundTaskBus(session=session, app=self._app)
