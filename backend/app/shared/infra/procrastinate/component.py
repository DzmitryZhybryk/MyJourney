"""
Procrastinate App + Component.

App создаётся внутри компонента; module-level singleton'а нет — это снимает
зависимость shared/ от глобального settings и от конкретных доменных tasks.

Domain-tasks объявляются через локальные ``Blueprint``-инстансы в каждом
домене (``app/<domain>/infra/tasks.py``). Composition root собирает blueprints
и передаёт их в ``ProcrastinateComponent``; внутри ``add_tasks_from`` копирует
декларации в App.

Драйвер psycopg3 (async) выбран сознательно: позволяет atomic defer
из той же SQLAlchemy-сессии (см. ``SessionBoundTaskBusPort``).
"""

from collections.abc import Sequence
from typing import Final

from procrastinate import App, Blueprint, PsycopgConnector

from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.settings import ProcrastinateSettings

# Единственный ключ ``additional_context`` воркера: под ним лежит весь реестр компонентов,
# таска достаёт из него нужное по классу, а не по своей строке на каждую зависимость.
WORKER_REGISTRY_KEY: Final[str] = "registry"


class ProcrastinateApp(App):
    """Typed alias для использования как ключ в ComponentRegistry."""


class ProcrastinateComponent(BaseComponent):
    def __init__(
        self,
        *,
        settings: ProcrastinateSettings,
        blueprints: Sequence[Blueprint] = (),
    ) -> None:
        """
        Создаёт App-инстанс и регистрирует blueprints.

        Args:
            settings: Procrastinate-конфиг (pool/worker) + унаследованный PG DSN.
            blueprints: Доменные blueprint'ы с декларациями tasks. Пустой —
                компонент поднимается без tasks (валидно для процесса, которому
                нужно только соединение с очередью, например для шага схемы).
        """
        self._app = ProcrastinateApp(
            connector=PsycopgConnector(
                conninfo=settings.postgres_libpq_dsn,
                min_size=settings.PROCRASTINATE_POOL_MIN_SIZE,
                max_size=settings.PROCRASTINATE_POOL_MAX_SIZE,
            ),
        )

        for blueprint in blueprints:
            self._app.add_tasks_from(blueprint, namespace="")

    async def startup(self, registry: ComponentRegistry) -> None:
        try:
            await self._app.open_async()
        except BaseException:
            # Коннектор присваивает пул до ожидания первых соединений. На таймауте psycopg_pool закрывает
            # пул сам, но при отмене ожидания (SIGINT на старте) пул остаётся открытым с фоновыми воркерами,
            # а shutdown упавшего компонента никто не вызовет.
            await self._app.close_async()
            raise

        registry.set(key=ProcrastinateApp, value=self._app)

    async def shutdown(self) -> None:
        await self._app.close_async()
