"""
Worker entrypoint для procrastinate-задач.

Поднимает только те компоненты, которые нужны исполнителю tasks:
``ResendComponent`` (даёт ``EmailTransportPort``), ``MediaStorageComponent``
(хранилища бакетов media) и ``ProcrastinateComponent``
(App + подключённые blueprint'ы доменов). ``SqlAlchemyComponent`` намеренно
отсутствует — текущая task ``send_verification_email`` БД не трогает:
расшифровывает код ключом из настроек, рендерит письмо и зовёт provider.

Таски получают зависимости из реестра компонентов: он целиком лежит в
``additional_context`` под ``WORKER_REGISTRY_KEY``.

Schema procrastinate worker не трогает: её применяет шаг миграции
(``python -m app.shared.infra.procrastinate`` после ``alembic upgrade head``).

Процесс блокируется в ``run_worker_async`` до SIGTERM/SIGINT; procrastinate
сам graceful-shutdown'ит in-flight jobs, после чего ``run_components``
освобождает ресурсы компонентов (psycopg-пул, httpx-пул, клиент S3) в обратном порядке.
"""

import asyncio

from app.blueprints import TASK_BLUEPRINTS
from app.media.infra.component import MediaStorageComponent
from app.shared.enums import AppEnvEnum
from app.shared.infra.di.base import BaseComponent
from app.shared.infra.di.lifecycle import run_components
from app.shared.infra.di.registry import ComponentRegistry
from app.shared.infra.email.component import ResendComponent
from app.shared.infra.procrastinate.component import WORKER_REGISTRY_KEY, ProcrastinateApp, ProcrastinateComponent
from app.shared.logging import configure_logging, get_logger
from app.shared.settings import settings

logger = get_logger(__name__)


async def run_worker() -> None:  # pragma: no cover — entry-point обвязка (компоненты+run), не unit-тестируется
    """
    Поднимает компоненты и запускает procrastinate-worker.

    Scenarios:
        - запуск воркера фоновых задач
    """
    configure_logging(include_debug=settings.ENVIRONMENT in (AppEnvEnum.LOCAL, AppEnvEnum.DEVELOPMENT))

    registry = ComponentRegistry()
    components: list[BaseComponent] = [
        ResendComponent(settings=settings),
        MediaStorageComponent(settings=settings),
        ProcrastinateComponent(settings=settings, blueprints=TASK_BLUEPRINTS),
    ]
    async with run_components(components=components, registry=registry):
        logger.info("worker.starting", concurrency=settings.PROCRASTINATE_WORKER_CONCURRENCY)
        await registry.get(ProcrastinateApp).run_worker_async(
            concurrency=settings.PROCRASTINATE_WORKER_CONCURRENCY,
            additional_context={WORKER_REGISTRY_KEY: registry},
        )


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(run_worker())
