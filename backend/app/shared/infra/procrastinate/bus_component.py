"""
TaskBusComponent — lifecycle-обёртка над ``TaskBusPort``.

На startup читает ``ProcrastinateApp`` из registry и регистрирует ``ProcrastinateTaskBus``
(реализацию ``TaskBusPort``) под ключом impl-класса.
Регистрируется **после** ``ProcrastinateComponent`` в композиции компонентов —
иначе на startup'е ``ProcrastinateApp`` ещё не будет в registry.

shutdown — no-op: ``TaskBusPort`` собственным сетевым ресурсом не владеет, коннекшен
закрывает ``ProcrastinateComponent.shutdown``.
"""

from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.procrastinate.bus import ProcrastinateTaskBus
from app.shared.infra.procrastinate.component import ProcrastinateApp


class TaskBusComponent(BaseComponent):
    async def startup(self, registry: ComponentRegistry) -> None:
        app = registry.get(ProcrastinateApp)
        registry.set(key=ProcrastinateTaskBus, value=ProcrastinateTaskBus(app=app))

    async def shutdown(self) -> None:
        pass
