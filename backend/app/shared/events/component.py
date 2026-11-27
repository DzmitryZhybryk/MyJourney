"""
EventPublisherComponent — lifecycle-обёртка над ``EventPublisherPort``.

На startup читает ``ProcrastinateTaskBus`` из registry и регистрирует ``TaskBusEventPublisher`` под ключом
impl-класса. Регистрируется **после** ``TaskBusComponent`` — иначе шины ещё нет в registry.

shutdown — no-op: собственным ресурсом издатель не владеет.
"""

from app.shared.events.publisher import EventSubscriptions, TaskBusEventPublisher
from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.procrastinate.bus import ProcrastinateTaskBus


class EventPublisherComponent(BaseComponent):
    def __init__(self, subscriptions: EventSubscriptions) -> None:
        self._subscriptions = subscriptions

    async def startup(self, registry: ComponentRegistry) -> None:
        task_bus = registry.get(ProcrastinateTaskBus)
        registry.set(
            key=TaskBusEventPublisher,
            value=TaskBusEventPublisher(task_bus=task_bus, subscriptions=self._subscriptions),
        )

    async def shutdown(self) -> None:
        pass
