"""
Протоколы шины задач для application-слоя.

Вертикаль procrastinate сама владеет своими протоколами (как ``crypto`` —
``SaltedHasherPort``): application зависит от Protocol'ов ``TaskBusPort`` /
``SessionBoundTaskBusPort``, а конкретная реализация на procrastinate живёт в ``bus.py``.
Тесты подставляют фейк, реализующий тот же Protocol, без наследования impl.

Контракт расщеплён на два по зависимостям:

- ``TaskBusPort`` — defer вне транзакции (fire-and-forget). Для atomic defer'а в
  текущей SA-транзакции — ``TaskBusPort.bind_to(session) -> SessionBoundTaskBusPort``.
- ``SessionBoundTaskBusPort`` — view, привязанный к ``AsyncSession``: defer попадает
  в ту же транзакцию, что и pending writes. Commit'ит ``UnitOfWork``.

Зависимость зашита в тип — каждый новый метод попадает в правильный контракт
без обсуждений: не нужна сессия → ``TaskBusPort``; нужна активная SA-tx →
``SessionBoundTaskBusPort``.
"""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SessionBoundTaskBusPort(Protocol):
    """Контракт defer'а procrastinate-таски в текущей SA-транзакции."""

    async def defer(self, *, task_name: str, lock: str | None = None, **task_kwargs: Any) -> None:
        """
        Ставит задачу в той же транзакции, что и записи use case'а; фиксирует её commit UnitOfWork.

        Scenarios:
            - use case, который ставит фоновую задачу атомарно со своими записями

        Args:
            task_name: Имя задачи
            lock: Lock-строка: одновременно выполняется только одна задача с ним; ``None`` — без lock'а
            **task_kwargs: Аргументы задачи
        """
        ...


class TaskBusPort(Protocol):
    """Контракт постановки procrastinate-задач: fire-and-forget defer и привязка к транзакции."""

    async def defer(self, *, task_name: str, lock: str | None = None, **task_kwargs: Any) -> None:
        """
        Ставит задачу вне транзакции.

        Scenarios:
            - фоновая задача, не связанная с записями use case'а; сейчас так задачи не ставит никто

        Args:
            task_name: Имя задачи
            lock: Lock-строка: одновременно выполняется только одна задача с ним; ``None`` — без lock'а
            **task_kwargs: Аргументы задачи
        """
        ...

    def bind_to(self, session: AsyncSession) -> SessionBoundTaskBusPort:
        """
        Привязывает постановку задач к транзакции сессии.

        Scenarios:
            - use case, который ставит фоновую задачу атомарно со своими записями

        Args:
            session: Активная сессия UnitOfWork

        Returns:
            Шина, чей ``defer`` попадает в транзакцию сессии
        """
        ...
