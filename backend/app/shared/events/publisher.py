"""
Издатель событий поверх шины задач: каждое событие — по задаче на подписчика в транзакции use case'а.

Контракты, на которые опирается application, — в ``ports.py``. Задача подписчика получает событие
JSON-словарём в аргументе ``event``.
"""

from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.events.event import IntegrationEvent
from app.shared.events.ports import EventPublisherPort, SessionBoundEventPublisherPort
from app.shared.infra.procrastinate import SessionBoundTaskBusPort, TaskBusPort

type EventSubscriptions = Mapping[type[IntegrationEvent], tuple[str, ...]]


class TaskBusSessionBoundEventPublisher(SessionBoundEventPublisherPort):
    """Реализация ``SessionBoundEventPublisherPort``: задачи подписчиков ставятся в транзакции сессии."""

    def __init__(self, *, task_bus: SessionBoundTaskBusPort, subscriptions: EventSubscriptions) -> None:
        self._task_bus = task_bus
        self._subscriptions = subscriptions

    async def publish(self, event: IntegrationEvent) -> None:
        payload = event.model_dump(mode="json")
        for task_name in self._subscriptions.get(type(event), ()):
            await self._task_bus.defer(task_name=task_name, event=payload)


class TaskBusEventPublisher(EventPublisherPort):
    """Реализация ``EventPublisherPort`` поверх шины задач и таблицы подписок composition root'а."""

    def __init__(self, *, task_bus: TaskBusPort, subscriptions: EventSubscriptions) -> None:
        self._task_bus = task_bus
        self._subscriptions = subscriptions

    def bind_to(self, session: AsyncSession) -> SessionBoundEventPublisherPort:
        return TaskBusSessionBoundEventPublisher(
            task_bus=self._task_bus.bind_to(session),
            subscriptions=self._subscriptions,
        )
