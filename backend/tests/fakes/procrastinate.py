"""Фейки ``TaskBusPort`` / ``SessionBoundTaskBusPort`` с записью defer'ов для state-ассертов."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.procrastinate import SessionBoundTaskBusPort, TaskBusPort


@dataclass(frozen=True, slots=True)
class DeferredTask:
    """Запись одного defer'а: имя задачи, lock и переданные task-kwargs."""

    task_name: str
    lock: str | None
    kwargs: dict[str, Any]


class FakeSessionBoundTaskBus(SessionBoundTaskBusPort):
    """Сессионно-привязанный фейк: пишет defer'ы в ``deferred`` вместо постановки в очередь."""

    def __init__(self) -> None:
        self.deferred: list[DeferredTask] = []

    async def defer(self, *, task_name: str, lock: str | None = None, **task_kwargs: Any) -> None:
        self.deferred.append(DeferredTask(task_name=task_name, lock=lock, kwargs=task_kwargs))


class FakeTaskBus(TaskBusPort):
    """
    Фейк ``TaskBusPort``: ``bind_to`` запоминает переданную сессию и отдаёт один общий
    ``FakeSessionBoundTaskBus`` — тест проверяет и факт defer'а, и что он сделан в сессии UoW.
    """

    def __init__(self) -> None:
        self.bound = FakeSessionBoundTaskBus()
        self.bound_session: AsyncSession | None = None

    async def defer(self, *, task_name: str, lock: str | None = None, **task_kwargs: Any) -> None:
        self.bound.deferred.append(DeferredTask(task_name=task_name, lock=lock, kwargs=task_kwargs))

    def bind_to(self, session: AsyncSession) -> SessionBoundTaskBusPort:
        self.bound_session = session
        return self.bound
